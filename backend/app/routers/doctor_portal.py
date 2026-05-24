from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.orm.attributes import flag_modified

from app.database import get_db
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.visit import VisitRecord
from app.models.user import User
from app.services.auth import require_doctor_user

router = APIRouter(prefix="/doctor", tags=["Doctor Portal"])


def _now():
    return datetime.now(timezone.utc)


@router.get("/me")
def doctor_me(
    current_user: User = Depends(require_doctor_user),
    db: Session = Depends(get_db),
):
    doctor = db.query(Doctor).filter(Doctor.id == current_user.doctor_id).first()
    if not doctor:
        return {}
    return {
        "id": str(doctor.id),
        "name": doctor.name,
        "specialty": doctor.specialty,
        "qualification": doctor.qualification,
        "fee": doctor.fee,
        "bio": doctor.bio,
        "timings": doctor.timings or [],
        "treatments": doctor.treatments or [],
    }


@router.get("/stats")
def doctor_stats(
    current_user: User = Depends(require_doctor_user),
    db: Session = Depends(get_db),
):
    now = _now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    doctor_id = current_user.doctor_id

    total_appointments = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.is_active == True,
    ).count()

    today_count = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.is_active == True,
        Appointment.slot_datetime >= today_start,
        Appointment.slot_datetime < today_end,
        Appointment.status.in_(["pending", "confirmed"]),
    ).count()

    total_visits = db.query(VisitRecord).filter(
        VisitRecord.doctor_id == doctor_id,
        VisitRecord.is_active == True,
    ).count()

    total_patients = db.query(VisitRecord.patient_id).filter(
        VisitRecord.doctor_id == doctor_id,
        VisitRecord.is_active == True,
    ).distinct().count()

    return {
        "total_appointments": total_appointments,
        "today_appointments": today_count,
        "total_visits": total_visits,
        "total_patients": total_patients,
    }


@router.get("/schedule")
def doctor_schedule(
    current_user: User = Depends(require_doctor_user),
    db: Session = Depends(get_db),
):
    now = _now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = today_start + timedelta(days=7)

    appointments = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == current_user.doctor_id,
            Appointment.is_active == True,
            Appointment.slot_datetime >= today_start,
            Appointment.slot_datetime < week_end,
        )
        .order_by(Appointment.slot_datetime.asc())
        .all()
    )

    today_str = today_start.date().isoformat()
    today_appts = []
    upcoming_appts = []

    for a in appointments:
        slot_date = a.slot_datetime.date().isoformat() if a.slot_datetime else None
        row = {
            "id": str(a.id),
            "patient_name": a.patient_name,
            "patient_phone": a.patient_phone,
            "patient_concern": a.patient_concern,
            "slot_datetime": a.slot_datetime.isoformat() if a.slot_datetime else None,
            "status": a.status,
            "notes": a.notes or "",
        }
        if slot_date == today_str:
            today_appts.append(row)
        else:
            upcoming_appts.append(row)

    return {"today": today_appts, "upcoming": upcoming_appts}


@router.get("/patients")
def doctor_patients(
    current_user: User = Depends(require_doctor_user),
    db: Session = Depends(get_db),
):
    visits = (
        db.query(VisitRecord)
        .options(joinedload(VisitRecord.patient))
        .filter(
            VisitRecord.doctor_id == current_user.doctor_id,
            VisitRecord.is_active == True,
        )
        .order_by(VisitRecord.visit_date.desc())
        .all()
    )

    seen = set()
    patients = []
    for v in visits:
        if not v.patient or str(v.patient_id) in seen:
            continue
        seen.add(str(v.patient_id))
        patients.append({
            "id": str(v.patient.id),
            "name": v.patient.name,
            "phone": v.patient.phone,
            "last_visit": v.visit_date.isoformat() if v.visit_date else None,
            "complaint": v.complaint,
            "diagnosis": v.diagnosis,
        })

    return patients


class NotesUpdate(BaseModel):
    notes: str


@router.patch("/appointments/{appointment_id}/notes")
def save_appointment_notes(
    appointment_id: str,
    data: NotesUpdate,
    current_user: User = Depends(require_doctor_user),
    db: Session = Depends(get_db),
):
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.doctor_id == current_user.doctor_id,
    ).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    appointment.notes = data.notes.strip()
    db.commit()
    return {"message": "Notes saved."}


class AvailabilityUpdate(BaseModel):
    timings: list


@router.put("/availability")
def update_availability(
    data: AvailabilityUpdate,
    current_user: User = Depends(require_doctor_user),
    db: Session = Depends(get_db),
):
    doctor = db.query(Doctor).filter(Doctor.id == current_user.doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")

    doctor.timings = [dict(t) for t in data.timings]
    flag_modified(doctor, "timings")
    db.commit()
    return {"message": "Availability updated."}


@router.post("/ready")
def toggle_ready(
    current_user: User = Depends(require_doctor_user),
    db: Session = Depends(get_db),
):
    """Doctor signals they are ready for the next patient."""
    doctor = db.query(Doctor).filter(Doctor.id == current_user.doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")
    doctor.is_ready = not doctor.is_ready
    db.commit()
    return {"is_ready": doctor.is_ready}


@router.get("/my-queue")
def my_queue(
    current_user: User = Depends(require_doctor_user),
    db: Session = Depends(get_db),
):
    """Today's checked-in patients waiting for this doctor."""
    from app.models.appointment import Appointment
    now = _now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    appointments = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == current_user.doctor_id,
            Appointment.is_active == True,
            Appointment.slot_datetime >= today_start,
            Appointment.slot_datetime < today_end,
        )
        .order_by(Appointment.checked_in_at.asc().nullslast(), Appointment.slot_datetime.asc())
        .all()
    )

    doctor = db.query(Doctor).filter(Doctor.id == current_user.doctor_id).first()

    waiting = []
    with_doctor = []
    done = []

    for a in appointments:
        entry = {
            "id": str(a.id),
            "patient_name": a.patient_name,
            "patient_phone": a.patient_phone,
            "patient_concern": a.patient_concern,
            "slot_datetime": a.slot_datetime.isoformat(),
            "status": a.status,
            "checked_in": a.checked_in,
            "checked_in_at": a.checked_in_at.isoformat() if a.checked_in_at else None,
            "wait_minutes": int((now - a.checked_in_at).total_seconds() // 60)
                            if a.checked_in and a.checked_in_at else None,
        }
        if a.status == "in_progress":
            with_doctor.append(entry)
        elif a.status in ("completed", "cancelled", "no_show"):
            done.append(entry)
        elif a.checked_in:
            waiting.append(entry)

    return {
        "is_ready": doctor.is_ready if doctor else False,
        "waiting": waiting,
        "with_doctor": with_doctor,
        "done_count": len(done),
    }
