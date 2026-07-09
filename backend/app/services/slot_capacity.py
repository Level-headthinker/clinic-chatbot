"""Per-doctor slot capacity — the single source of truth for "is this slot free?"

A slot can hold ``doctor.slot_capacity`` patients (default 1). Each active booking
claims a distinct seat (``slot_index`` 0..capacity-1). The partial UNIQUE index
``uq_active_appointment_slot`` makes seat-claiming race-safe: if two bookings race
for the same seat, one commit wins and the other raises IntegrityError.

Booking paths call ``claim_seat`` to reserve the next free seat, then commit; on
IntegrityError (lost race) they retry — ``book_with_retry`` wraps that.
"""
from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.appointment import Appointment

BOOKED_STATUSES = ["pending", "confirmed"]


def capacity_of(doctor) -> int:
    """A doctor's per-slot capacity, clamped to at least 1."""
    return max(1, int(getattr(doctor, "slot_capacity", 1) or 1))


def seats_taken(db: Session, tenant_id, doctor_id, slot) -> int:
    """How many active bookings already occupy this doctor's slot."""
    return db.query(Appointment).filter(
        Appointment.tenant_id == tenant_id,
        Appointment.doctor_id == doctor_id,
        Appointment.slot_datetime == slot,
        Appointment.status.in_(BOOKED_STATUSES),
    ).count()


def slot_has_room(db: Session, doctor, tenant_id, slot) -> bool:
    """True if the slot can still take at least one more patient."""
    return seats_taken(db, tenant_id, doctor.id, slot) < capacity_of(doctor)


def next_free_seat(db: Session, doctor, tenant_id, slot) -> int | None:
    """The next unclaimed seat index for this slot, or None if the slot is full.

    Uses the taken-count as the candidate index; the unique index is what
    ultimately guarantees no two bookings keep the same seat under a race.
    """
    taken = seats_taken(db, tenant_id, doctor.id, slot)
    return taken if taken < capacity_of(doctor) else None


def book_with_retry(db: Session, doctor, tenant_id, slot, build_appointment,
                    *, max_attempts: int = 5):
    """Reserve the next free seat and persist the appointment, race-safely.

    ``build_appointment(seat_index)`` must return a new (unsaved) Appointment.
    Returns the committed Appointment, or None if the slot is full / every seat
    was lost to concurrent bookers. The caller owns nothing else on the session.
    """
    for _ in range(max_attempts):
        seat = next_free_seat(db, doctor, tenant_id, slot)
        if seat is None:
            return None  # full
        appt = build_appointment(seat)
        appt.slot_index = seat
        db.add(appt)
        try:
            db.commit()
            db.refresh(appt)
            return appt
        except IntegrityError:
            # Another booking took this exact seat first — recount and retry.
            db.rollback()
            continue
    return None
