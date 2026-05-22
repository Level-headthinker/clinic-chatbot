"""Public self-booking endpoint — no authentication required.

Patients visit /book/<branch-slug> on the frontend, fill a form,
and an appointment request is created directly in the database.
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.appointment import Appointment
from app.models.branch import Branch
from app.models.chat import Lead
from app.models.doctor import Doctor
from app.models.tenant import Tenant

router = APIRouter(prefix="/public", tags=["Public Booking"])

BOOKED_STATUSES = ["pending", "confirmed"]
WEEKDAY_BY_NAME = {
    "monday": 0, "tuesday": 1, "wednesday": 2,
    "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6,
}


def _parse_time(value):
    if not value:
        return None
    value = value.strip().upper().replace(".", "")
    for fmt in ("%I:%M %p", "%I %p", "%H:%M"):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    return None


def _next_slots(doctor, tenant_id, db, days_ahead=14, max_slots=5):
    now = datetime.now()
    booked = {
        r[0].replace(tzinfo=None)
        for r in db.query(Appointment.slot_datetime).filter(
            Appointment.tenant_id == tenant_id,
            Appointment.doctor_id == doctor.id,
            Appointment.status.in_(BOOKED_STATUSES),
            Appointment.slot_datetime >= now,
        ).all()
        if r[0]
    }
    slots = []
    for timing in doctor.timings or []:
        weekday = WEEKDAY_BY_NAME.get(str(timing.get("day", "")).strip().lower())
        start = _parse_time(timing.get("from"))
        end = _parse_time(timing.get("to"))
        if weekday is None or not start or not end:
            continue
        for offset in range(days_ahead + 1):
            day = (now + timedelta(days=offset)).date()
            if day.weekday() != weekday:
                continue
            slot = datetime.combine(day, start)
            slot_end = datetime.combine(day, end)
            while slot < slot_end:
                if slot > now and slot not in booked:
                    slots.append(slot)
                slot += timedelta(minutes=30)
    return sorted(slots)[:max_slots]


@router.get("/clinic/{slug}")
def get_clinic_info(slug: str, db: Session = Depends(get_db)):
    """Public: return clinic name, bot name, doctors list for the booking form."""
    branch = db.query(Branch).filter(
        Branch.slug == slug, Branch.is_active.is_(True)
    ).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Clinic not found")

    tenant = db.query(Tenant).filter(
        Tenant.id == branch.tenant_id, Tenant.is_active.is_(True)
    ).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Clinic not found")

    doctors = db.query(Doctor).filter(
        Doctor.tenant_id == tenant.id,
        Doctor.is_active.is_(True),
    ).all()

    return {
        "clinic_name": tenant.name,
        "bot_name": branch.bot_name or tenant.bot_name,
        "welcome_message": branch.welcome_message or tenant.welcome_message,
        "primary_color": tenant.primary_color,
        "doctors": [
            {
                "id": str(d.id),
                "name": d.name if d.name.lower().startswith("dr") else f"Dr. {d.name}",
                "specialty": d.specialty,
                "fee": d.fee,
                "timings": d.timings or [],
                "slots": [
                    s.strftime("%Y-%m-%dT%H:%M:%S")
                    for s in _next_slots(d, tenant.id, db)
                ],
            }
            for d in doctors
        ],
    }


class BookingRequest(BaseModel):
    patient_name: str
    patient_phone: str
    patient_concern: Optional[str] = ""
    doctor_id: str
    slot_datetime: str  # ISO format: "2026-05-25T10:00:00"


@router.post("/clinic/{slug}/book")
def create_booking(slug: str, data: BookingRequest, db: Session = Depends(get_db)):
    """Public: patient submits a booking request."""
    branch = db.query(Branch).filter(
        Branch.slug == slug, Branch.is_active.is_(True)
    ).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Clinic not found")

    tenant = db.query(Tenant).filter(
        Tenant.id == branch.tenant_id, Tenant.is_active.is_(True)
    ).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Clinic not found")

    doctor = db.query(Doctor).filter(
        Doctor.id == data.doctor_id,
        Doctor.tenant_id == tenant.id,
        Doctor.is_active.is_(True),
    ).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    # Check no duplicate active appointment
    active = db.query(Appointment).filter(
        Appointment.patient_phone == data.patient_phone,
        Appointment.tenant_id == tenant.id,
        Appointment.status.in_(BOOKED_STATUSES),
    ).first()
    if active:
        raise HTTPException(status_code=409, detail="You already have a pending appointment.")

    try:
        slot = datetime.fromisoformat(data.slot_datetime)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid slot datetime format.")

    appointment = Appointment(
        tenant_id=tenant.id,
        branch_id=branch.id,
        doctor_id=doctor.id,
        patient_name=data.patient_name.strip(),
        patient_phone=data.patient_phone.strip(),
        patient_concern=data.patient_concern or "Self-booked",
        slot_datetime=slot,
        status="pending",
    )
    db.add(appointment)

    # Also save as lead if new
    existing_lead = db.query(Lead).filter(
        Lead.phone == data.patient_phone, Lead.tenant_id == tenant.id
    ).first()
    if not existing_lead:
        db.add(Lead(
            tenant_id=tenant.id,
            branch_id=branch.id,
            name=data.patient_name.strip(),
            phone=data.patient_phone.strip(),
            concern=data.patient_concern or "Self-booked",
            source="self_booking",
            status="new",
        ))

    db.commit()

    doctor_name = doctor.name if doctor.name.lower().startswith("dr") else f"Dr. {doctor.name}"
    return {
        "message": "Appointment request submitted successfully.",
        "doctor": doctor_name,
        "slot": slot.strftime("%A, %d %B %Y at %I:%M %p"),
    }
