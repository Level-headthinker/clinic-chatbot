"""Public self-booking endpoint — no authentication required.

Patients visit /book/<branch-slug> on the frontend, fill a form,
and an appointment request is created directly in the database.
"""
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.appointment import Appointment
from app.models.branch import Branch
from app.models.chat import Lead
from app.models.doctor import Doctor
from app.models.tenant import Tenant

router = APIRouter(prefix="/public", tags=["Public Booking"])

# ── Public-endpoint rate limiter (per IP) ─────────────────────────────────────
# In-memory: per-process, resets on restart. Upgrade path: Redis (see AUDIT_REPORT).
_booking_attempts: dict[str, list[float]] = defaultdict(list)


def _booking_rate_limit(request: Request, max_attempts: int = 10, window: int = 3600):
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    attempts = [t for t in _booking_attempts[ip] if t > now - window]
    _booking_attempts[ip] = attempts
    if len(attempts) >= max_attempts:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many booking attempts. Please try again later or call the clinic.",
        )
    _booking_attempts[ip].append(now)

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


def _slot_is_offered(doctor, slot: datetime, db, tenant_id) -> bool:
    """A public booking may only claim a slot the doctor actually offers:
    future, on a working day, inside working hours, on the 30-minute grid,
    and not already taken. Without this check anyone could write arbitrary
    datetimes (3 AM, past dates, double-books) straight into the clinic's diary."""
    now = datetime.now()
    if slot <= now:
        return False
    if slot > now + timedelta(days=60):
        return False
    from app.services.slot_capacity import slot_has_room
    if not slot_has_room(db, doctor, tenant_id, slot):
        return False  # slot at capacity
    for timing in doctor.timings or []:
        weekday = WEEKDAY_BY_NAME.get(str(timing.get("day", "")).strip().lower())
        start = _parse_time(timing.get("from"))
        end = _parse_time(timing.get("to"))
        if weekday is None or not start or not end:
            continue
        if slot.weekday() != weekday:
            continue
        day_start = datetime.combine(slot.date(), start)
        day_end = datetime.combine(slot.date(), end)
        if day_start <= slot < day_end and \
                int((slot - day_start).total_seconds()) % 1800 == 0:
            return True
    return False


_PHONE_OK = re.compile(r"^\+?[0-9][0-9\-\s]{6,18}$")


class BookingRequest(BaseModel):
    patient_name: str = Field(min_length=2, max_length=255)
    patient_phone: str = Field(min_length=7, max_length=20)
    patient_concern: Optional[str] = Field(default="", max_length=500)
    doctor_id: str
    slot_datetime: str  # ISO format: "2026-05-25T10:00:00"


@router.post("/clinic/{slug}/book")
def create_booking(
    slug: str,
    data: BookingRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Public: patient submits a booking request."""
    _booking_rate_limit(request)
    if not _PHONE_OK.match(data.patient_phone.strip()):
        raise HTTPException(status_code=400, detail="Please enter a valid phone number.")
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
    if slot.tzinfo is not None:
        slot = slot.replace(tzinfo=None)

    if not _slot_is_offered(doctor, slot, db, tenant.id):
        raise HTTPException(
            status_code=409,
            detail="That slot is not available. Please pick one of the offered slots.",
        )

    from app.services.slot_capacity import next_free_seat
    seat = next_free_seat(db, doctor, tenant.id, slot)
    if seat is None:
        raise HTTPException(
            status_code=409,
            detail="That slot just filled up. Please pick another slot.",
        )
    appointment = Appointment(
        tenant_id=tenant.id,
        branch_id=branch.id,
        doctor_id=doctor.id,
        patient_name=data.patient_name.strip(),
        patient_phone=data.patient_phone.strip(),
        patient_concern=data.patient_concern or "Self-booked",
        slot_datetime=slot,
        slot_index=seat,
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

    try:
        db.commit()
    except IntegrityError:
        # Lost the seat to a concurrent booker between the check and the commit.
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="That slot just filled up. Please pick another slot.",
        )

    doctor_name = doctor.name if doctor.name.lower().startswith("dr") else f"Dr. {doctor.name}"
    return {
        "message": "Appointment request submitted successfully.",
        "doctor": doctor_name,
        "slot": slot.strftime("%A, %d %B %Y at %I:%M %p"),
    }
