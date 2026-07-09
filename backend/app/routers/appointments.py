# Handles booking appointments. Two types of users hit these endpoints
#  — the chatbot books on behalf of patients,
#  and the admin manages bookings from the dashboard.

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta
from app.database import get_db
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.room import Room
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import require_admin_user
from app.services.messaging import send_whatsapp

router = APIRouter(prefix="/appointments", tags=["Appointments"])


class AppointmentCreate(BaseModel):
    doctor_id: str
    patient_name: str
    patient_phone: str
    patient_concern: Optional[str] = None
    slot_datetime: datetime


class AppointmentUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


@router.post("/book")
def book_appointment(
    data: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user)
):
    doctor = db.query(Doctor).filter(
        Doctor.id == data.doctor_id,
        Doctor.tenant_id == current_user.tenant_id,
        Doctor.is_active == True
    ).first()
    if not doctor:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found"
        )

    from app.services.slot_capacity import next_free_seat
    seat = next_free_seat(db, doctor, current_user.tenant_id, data.slot_datetime)
    if seat is None:
        raise HTTPException(
            status_code=400,
            detail="This slot is already full"
        )

    appointment = Appointment(
        tenant_id=current_user.tenant_id,
        branch_id=current_user.branch_id or doctor.branch_id,
        doctor_id=data.doctor_id,
        patient_name=data.patient_name,
        patient_phone=data.patient_phone,
        patient_concern=data.patient_concern,
        slot_datetime=data.slot_datetime,
        slot_index=seat,
        status="pending"
    )
    db.add(appointment)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="This slot is already booked"
        )
    db.refresh(appointment)

    return {
        "message": "Appointment booked successfully",
        "appointment_id": str(appointment.id),
        "status": appointment.status,
        "slot": str(appointment.slot_datetime)
    }


@router.get("/")
def list_appointments(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user)
):
    query = db.query(Appointment).options(
        joinedload(Appointment.doctor)
    ).filter(
        Appointment.tenant_id == current_user.tenant_id,
        Appointment.is_active == True,
    )
    if current_user.branch_id is not None:
        query = query.filter(Appointment.branch_id == current_user.branch_id)
    if status:
        query = query.filter(Appointment.status == status)

    appointments = query.order_by(
        Appointment.slot_datetime.asc()
    ).all()

    return [
        {
            "id": str(a.id),
            "patient_name": a.patient_name,
            "patient_phone": a.patient_phone,
            "alternate_phone": a.alternate_phone,
            "patient_concern": a.patient_concern,
            "doctor_id": str(a.doctor_id),
            "doctor_name": a.doctor.name,
            "doctor_specialty": a.doctor.specialty,
            "doctor_fee": a.doctor.fee,
            "slot_datetime": str(a.slot_datetime),
            "status": a.status,
            "notes": a.notes,
            "reminder_sent": a.reminder_sent,
            "created_at": str(a.created_at)
        }
        for a in appointments
    ]


@router.put("/{appointment_id}")
def update_appointment(
    appointment_id: str,
    data: AppointmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user)
):
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.tenant_id == current_user.tenant_id
    ).first()
    if not appointment:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found"
        )

    if data.status is not None:
        allowed = ["pending", "confirmed", "cancelled", "completed", "no_show", "in_progress"]
        if data.status not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Status must be one of {allowed}"
            )
        appointment.status = data.status

        # Free the room when appointment ends
        if data.status in ("completed", "cancelled", "no_show") and appointment.room_id:
            room = db.query(Room).filter(Room.id == appointment.room_id).first()
            if room:
                room.is_occupied = False
                room.current_appointment_id = None

    if data.notes is not None:
        appointment.notes = data.notes

    freed = data.status in ("cancelled", "no_show")
    db.commit()

    # A cancellation frees the slot — offer it to patients booked for the same
    # time on a later day (first to reply YES gets moved earlier). Best-effort.
    if freed:
        from app.services.slot_backfill import offer_freed_slot
        offer_freed_slot(db, appointment)

    return {"message": "Appointment updated successfully"}


@router.post("/{appointment_id}/remind")
def send_reminder(
    appointment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.tenant_id == current_user.tenant_id,
    ).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    doctor = db.query(Doctor).filter(Doctor.id == appointment.doctor_id).first()

    clinic_name = tenant.name if tenant else "the clinic"
    doctor_name = doctor.name if doctor else "your doctor"
    if doctor_name and not doctor_name.lower().startswith("dr"):
        doctor_name = f"Dr. {doctor_name}"

    slot_str = appointment.slot_datetime.strftime("%A, %d %B at %I:%M %p")
    message = (
        f"Hi {appointment.patient_name}! 👋\n\n"
        f"This is a reminder from {clinic_name}.\n"
        f"Your appointment with {doctor_name} is scheduled for:\n"
        f"📅 {slot_str}\n\n"
        f"Please arrive 10 minutes early. "
        f"To reschedule, reply to this message or call us directly."
    )

    sent = send_whatsapp(appointment.patient_phone, message)
    if not sent:
        raise HTTPException(status_code=503, detail="WhatsApp not configured. Add META credentials in .env.")

    appointment.reminder_sent = True
    db.commit()
    return {"message": "Reminder sent successfully."}


@router.delete("/{appointment_id}")
def cancel_appointment(
    appointment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user)
):
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.tenant_id == current_user.tenant_id
    ).first()
    if not appointment:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found"
        )

    appointment.status = "cancelled"
    db.commit()
    return {"message": "Appointment cancelled"}


# ── Waiting Room Queue ────────────────────────────────────────────────────────

def _fmt_appt(a, doctor_obj=None, room_map=None):
    wait_mins = None
    if a.checked_in and a.checked_in_at:
        delta = datetime.now(timezone.utc) - a.checked_in_at
        wait_mins = int(delta.total_seconds() // 60)
    doc = doctor_obj or a.doctor
    room_name = None
    if a.room_id and room_map:
        room_name = room_map.get(str(a.room_id))
    return {
        "id": str(a.id),
        "patient_name": a.patient_name,
        "patient_phone": a.patient_phone,
        "alternate_phone": a.alternate_phone,
        "patient_concern": a.patient_concern,
        "service_name": a.service_name,
        "doctor_name": doc.name if doc else "—",
        "doctor_id": str(a.doctor_id),
        "doctor_is_ready": doc.is_ready if doc else False,
        "slot_datetime": a.slot_datetime.isoformat(),
        "status": a.status,
        "checked_in": a.checked_in,
        "checked_in_at": a.checked_in_at.isoformat() if a.checked_in_at else None,
        "wait_minutes": wait_mins,
        "room_id": str(a.room_id) if a.room_id else None,
        "room_name": room_name,
    }


@router.get("/queue")
def get_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    base = (
        db.query(Appointment)
        .options(joinedload(Appointment.doctor))
        .filter(
            Appointment.tenant_id == current_user.tenant_id,
            Appointment.is_active == True,
            Appointment.slot_datetime >= today_start,
            Appointment.slot_datetime < today_end,
        )
    )
    if current_user.branch_id:
        base = base.filter(Appointment.branch_id == current_user.branch_id)

    all_today = base.order_by(Appointment.slot_datetime.asc()).all()

    # Build a room name lookup for any appointments with room_id
    room_ids = {str(a.room_id) for a in all_today if a.room_id}
    room_map = {}
    if room_ids:
        rooms = db.query(Room).filter(Room.id.in_(list(room_ids))).all()
        room_map = {str(r.id): r.name for r in rooms}

    expected    = [_fmt_appt(a, room_map=room_map) for a in all_today
                   if not a.checked_in and a.status in ("pending", "confirmed")]
    waiting     = sorted(
        [_fmt_appt(a, room_map=room_map) for a in all_today
         if a.checked_in and a.status in ("pending", "confirmed")],
        key=lambda x: x["checked_in_at"] or ""
    )
    with_doctor = [_fmt_appt(a, room_map=room_map) for a in all_today if a.status == "in_progress"]
    done        = [_fmt_appt(a, room_map=room_map) for a in all_today
                   if a.status in ("completed", "cancelled", "no_show")]

    return {"expected": expected, "waiting": waiting, "with_doctor": with_doctor, "done": done}


@router.post("/{appointment_id}/call-in")
def call_in_patient(
    appointment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    """Receptionist sends patient into doctor's room. Clears doctor's ready flag."""
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.tenant_id == current_user.tenant_id,
    ).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    appointment.status = "in_progress"

    # Clear the doctor's ready flag — they now have a patient
    doctor = db.query(Doctor).filter(Doctor.id == appointment.doctor_id).first()
    if doctor:
        doctor.is_ready = False

    db.commit()
    return {"message": "Patient called in."}


@router.post("/{appointment_id}/checkin")
def toggle_checkin(
    appointment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.tenant_id == current_user.tenant_id,
    ).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if appointment.checked_in:
        appointment.checked_in = False
        appointment.checked_in_at = None
    else:
        appointment.checked_in = True
        appointment.checked_in_at = datetime.now(timezone.utc)

    db.commit()
    return {"checked_in": appointment.checked_in}


# ── Walk-in / Service-based assignment ───────────────────────────────────────

@router.get("/available-for/{service_name}")
def available_for_service(
    service_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    """
    Returns doctors who can perform the requested service and free rooms.
    A doctor is available if:
      - They have the service name in their treatments list (case-insensitive)
      - They are not currently in_progress with another patient
    A room is available if it is not occupied.
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    # Doctors with this service in treatments
    all_doctors = db.query(Doctor).filter(
        Doctor.tenant_id == current_user.tenant_id,
        Doctor.is_active == True,
    ).all()
    if current_user.branch_id:
        all_doctors = [d for d in all_doctors if d.branch_id == current_user.branch_id]

    svc_lower = service_name.lower().strip()
    matched_doctors = [
        d for d in all_doctors
        if d.treatments and any(svc_lower in t.lower() for t in d.treatments)
    ]

    # Which of those doctors are currently busy (in_progress today)?
    busy_doctor_ids = {
        str(a.doctor_id)
        for a in db.query(Appointment).filter(
            Appointment.tenant_id == current_user.tenant_id,
            Appointment.status == "in_progress",
            Appointment.slot_datetime >= today_start,
            Appointment.slot_datetime < today_end,
        ).all()
    }

    available_doctors = [
        {
            "id": str(d.id),
            "name": d.name,
            "specialty": d.specialty,
            "is_ready": d.is_ready,
            "is_busy": str(d.id) in busy_doctor_ids,
        }
        for d in matched_doctors
    ]

    # Free rooms
    room_q = db.query(Room).filter(
        Room.tenant_id == current_user.tenant_id,
        Room.is_active == True,
        Room.is_occupied == False,
    )
    if current_user.branch_id:
        room_q = room_q.filter(Room.branch_id == current_user.branch_id)
    free_rooms = [{"id": str(r.id), "name": r.name} for r in room_q.order_by(Room.name).all()]

    return {
        "service": service_name,
        "doctors": available_doctors,
        "rooms": free_rooms,
    }


class WalkInCreate(BaseModel):
    patient_name: str
    patient_phone: str
    patient_concern: Optional[str] = None
    service_name: str
    doctor_id: str
    room_id: Optional[str] = None


@router.post("/walk-in")
def create_walk_in(
    data: WalkInCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    """Immediately assign a walk-in patient to a doctor and optional room."""
    doctor = db.query(Doctor).filter(
        Doctor.id == data.doctor_id,
        Doctor.tenant_id == current_user.tenant_id,
        Doctor.is_active == True,
    ).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    room = None
    if data.room_id:
        room = db.query(Room).filter(
            Room.id == data.room_id,
            Room.tenant_id == current_user.tenant_id,
            Room.is_active == True,
        ).first()
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        if room.is_occupied:
            raise HTTPException(status_code=400, detail="Room is already occupied")

    now = datetime.now(timezone.utc)
    appointment = Appointment(
        tenant_id=current_user.tenant_id,
        branch_id=current_user.branch_id or doctor.branch_id,
        doctor_id=data.doctor_id,
        patient_name=data.patient_name,
        patient_phone=data.patient_phone,
        patient_concern=data.patient_concern or data.service_name,
        service_name=data.service_name,
        slot_datetime=now,
        status="in_progress",
        checked_in=True,
        checked_in_at=now,
        room_id=room.id if room else None,
    )
    db.add(appointment)
    db.flush()

    if room:
        room.is_occupied = True
        room.current_appointment_id = appointment.id

    # Clear doctor's ready flag — they now have a patient
    doctor.is_ready = False

    db.commit()
    db.refresh(appointment)
    return {
        "message": "Walk-in assigned successfully.",
        "appointment_id": str(appointment.id),
        "doctor": doctor.name,
        "room": room.name if room else None,
    }
