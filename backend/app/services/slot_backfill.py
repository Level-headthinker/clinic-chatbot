"""Cancellation backfill — when a patient frees a slot, offer it to patients
booked for the same time on a later day, so a no-show/cancellation doesn't waste
the slot.

Design (chosen): offer the freed slot to *tomorrow's* patients; first to reply
YES gets moved earlier. A SlotOffer row tracks each outstanding offer so a freed
seat is only ever handed out once, even if several people reply.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.slot_offer import SlotOffer
from app.models.tenant import Tenant
from app.services.slot_capacity import next_free_seat, BOOKED_STATUSES

# Don't spam an entire waitlist — offer to at most this many upcoming patients.
_MAX_OFFERS = 3


def offer_freed_slot(db: Session, freed: Appointment) -> int:
    """A slot just freed (``freed`` was cancelled). Offer it to patients booked
    for the SAME doctor + same time-of-day on a later day. Returns how many
    offers were sent. Best-effort — never raises into the caller."""
    try:
        slot = freed.slot_datetime
        if not slot:
            return 0
        naive = slot.replace(tzinfo=None) if slot.tzinfo else slot
        if naive <= datetime.now():
            return 0  # freed slot already in the past — nothing to offer

        # Candidates: same doctor, still-active, a LATER calendar day but the same
        # clock time (so moving them "earlier to today" makes sense).
        candidates = db.query(Appointment).filter(
            Appointment.tenant_id == freed.tenant_id,
            Appointment.doctor_id == freed.doctor_id,
            Appointment.status.in_(BOOKED_STATUSES),
            Appointment.slot_datetime > slot,
            Appointment.id != freed.id,
        ).order_by(Appointment.slot_datetime.asc()).all()

        sent = 0
        for appt in candidates:
            if sent >= _MAX_OFFERS:
                break
            a = appt.slot_datetime
            a_naive = a.replace(tzinfo=None) if a and a.tzinfo else a
            if not a_naive or a_naive.time() != naive.time() or a_naive.date() <= naive.date():
                continue
            # Skip if this patient already has a pending offer for this slot.
            exists = db.query(SlotOffer).filter(
                SlotOffer.tenant_id == freed.tenant_id,
                SlotOffer.appointment_id == appt.id,
                SlotOffer.status == "pending",
            ).first()
            if exists:
                continue
            offer = SlotOffer(
                tenant_id=freed.tenant_id, branch_id=appt.branch_id,
                doctor_id=freed.doctor_id, patient_phone=appt.patient_phone,
                appointment_id=appt.id, offered_slot=slot,
                status="pending", expires_at=slot,
            )
            db.add(offer)
            db.flush()
            if _send_offer_message(db, freed.tenant_id, appt, slot):
                sent += 1
        db.commit()
        return sent
    except Exception as e:
        db.rollback()
        from app.observability import report_error
        report_error("Slot backfill offer failed", e, appointment=str(freed.id))
        return 0


def pending_offer_for(db: Session, tenant_id, phone: str) -> SlotOffer | None:
    """The most recent live offer for this patient (used by the chat brain)."""
    now = datetime.now()
    offer = db.query(SlotOffer).filter(
        SlotOffer.tenant_id == tenant_id,
        SlotOffer.patient_phone == phone,
        SlotOffer.status == "pending",
    ).order_by(SlotOffer.created_at.desc()).first()
    if offer and offer.expires_at:
        exp = offer.expires_at.replace(tzinfo=None) if offer.expires_at.tzinfo else offer.expires_at
        if exp <= now:
            offer.status = "expired"
            db.commit()
            return None
    return offer


def accept_offer(db: Session, offer: SlotOffer):
    """Move the patient's appointment earlier into the freed slot, if it still has
    room. Returns (True, new_slot) on success, (False, reason) otherwise."""
    appt = db.query(Appointment).filter(Appointment.id == offer.appointment_id).first()
    if not appt or appt.status not in BOOKED_STATUSES:
        offer.status = "expired"
        db.commit()
        return False, "gone"
    doctor = None
    from app.models.doctor import Doctor
    doctor = db.query(Doctor).filter(Doctor.id == offer.doctor_id).first()
    seat = next_free_seat(db, doctor, offer.tenant_id, offer.offered_slot) if doctor else None
    if seat is None:
        offer.status = "filled"
        db.commit()
        return False, "filled"   # someone else already took the freed slot

    appt.slot_datetime = offer.offered_slot
    appt.slot_index = seat
    appt.reminder_sent = False
    offer.status = "accepted"
    # Any other pending offers for the same freed slot can't be honoured now.
    db.query(SlotOffer).filter(
        SlotOffer.tenant_id == offer.tenant_id,
        SlotOffer.offered_slot == offer.offered_slot,
        SlotOffer.status == "pending",
        SlotOffer.id != offer.id,
    ).update({SlotOffer.status: "filled"}, synchronize_session=False)
    try:
        db.commit()
    except Exception:
        db.rollback()
        return False, "filled"
    return True, offer.offered_slot


def decline_offer(db: Session, offer: SlotOffer) -> None:
    offer.status = "declined"
    db.commit()


def _send_offer_message(db: Session, tenant_id, appt: Appointment, slot: datetime) -> bool:
    """Message the patient about the earlier opening (best-effort, free-form —
    the patient booked recently so is usually inside the 24h window)."""
    try:
        from app.services.messaging import send_whatsapp, tenant_sender_pnid
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        clinic = tenant.name if tenant else "the clinic"
        when = slot.strftime("%A %d %b at %I:%M %p")
        msg = (
            f"Hi {appt.patient_name}! An earlier appointment just opened at {clinic}: "
            f"📅 {when}. Reply YES to move your appointment to this earlier time, "
            f"or ignore this to keep your current one."
        )
        pnid = tenant_sender_pnid(db, tenant_id)
        return bool(send_whatsapp(appt.patient_phone, msg, from_pnid=pnid))
    except Exception:
        return False
