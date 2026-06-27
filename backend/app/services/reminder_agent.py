"""Automatic reminder agent — the brain behind self-driving follow-ups.

Runs daily (from the scheduler) and, with no manual work, does two things:

  1. Next-visit reminders — for every patient whose visit record has a
     ``next_visit_date`` coming up, send a gentle WhatsApp reminder referencing
     their doctor and what the visit is for.
  2. Lead nudges — for every lead who enquired but never booked, send a gentle
     "still interested?" message a couple of days later.

Each action is recorded as a FollowUp row (kind = next_visit | lead_nudge) so it
shows up on the Follow-ups page and is never sent twice (the existence of that
row is the de-dup key). If the WhatsApp send fails — e.g. outside Meta's 24-hour
messaging window, which needs an approved template — the follow-up is still
created as ``pending`` so staff can reach out manually. Nothing here ever crashes
the scheduler.

Note on delivery: free-form WhatsApp messages only deliver inside the 24-hour
customer-service window. Reminders sent days later require a pre-approved message
template; until one is configured, those sends will be recorded as not-yet-sent
(the task is still created).
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from app.config import settings
from app.models.appointment import Appointment
from app.models.chat import Lead
from app.models.doctor import Doctor
from app.models.follow_up import FollowUp
from app.models.patient import Patient
from app.models.tenant import Tenant
from app.models.visit import VisitRecord
from app.services.messaging import send_whatsapp


# ── Message builders (pure — unit tested) ────────────────────────────────────────

def next_visit_message(patient_name, clinic_name, doctor_name, date_str, reason=None) -> str:
    who = f" with {doctor_name}" if doctor_name else ""
    lines = [
        f"Hi {patient_name}! 👋",
        "",
        f"A gentle reminder from {clinic_name}: your next visit{who} is coming up on {date_str}.",
    ]
    if reason:
        lines.append(f"It's for your {reason}.")
    lines += ["", "Reply here to confirm or reschedule — we look forward to seeing you. 🙂"]
    return "\n".join(lines)


def lead_nudge_message(name, clinic_name) -> str:
    return (
        f"Hi {name}! 👋\n\n"
        f"This is {clinic_name}. You recently reached out to us and we'd love to help. "
        f"Would you like to book an appointment, or do you have any questions?\n\n"
        f"Just reply here and we'll take care of it. 🙂"
    )


# ── Helpers ──────────────────────────────────────────────────────────────────────

def _clinic_name(db, tenant_id) -> str:
    t = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    return t.name if t else "the clinic"


def _doctor_label(name: str | None) -> str | None:
    if not name:
        return None
    return name if name.lower().startswith("dr") else f"Dr. {name}"


def _record_followup(db, *, tenant_id, branch_id, kind, title, notes, due_date,
                     patient_id=None, lead_id=None, visit_id=None,
                     phone=None, message=None) -> bool:
    """Send the WhatsApp message (best-effort) and log the follow-up. Returns
    True if the message was actually delivered."""
    sent_at = None
    channel = None
    status = "pending"
    if phone and message:
        try:
            if send_whatsapp(phone, message):     # False = WA not configured
                sent_at = datetime.now(timezone.utc)
                channel = "whatsapp"
                status = "done"
        except Exception:
            # Delivery failed (e.g. outside 24h window) — keep as a pending task.
            pass

    db.add(FollowUp(
        tenant_id=tenant_id,
        branch_id=branch_id,
        patient_id=patient_id,
        lead_id=lead_id,
        visit_id=visit_id,
        title=title[:255],
        notes=notes,
        due_date=due_date,
        status=status,
        kind=kind,
        channel=channel,
        reminder_sent_at=sent_at,
    ))
    db.commit()
    return sent_at is not None


# ── Jobs ─────────────────────────────────────────────────────────────────────────

def _next_visit_reminders(db) -> dict:
    target = date.today() + timedelta(days=settings.NEXT_VISIT_REMINDER_DAYS_BEFORE)
    due_dt = datetime.combine(target, time(9, 0))

    visits = db.query(VisitRecord).filter(
        VisitRecord.next_visit_date == target,
        VisitRecord.is_active == True,
    ).all()

    created = sent = 0
    for v in visits:
        # De-dup: one next-visit reminder per visit.
        exists = db.query(FollowUp.id).filter(
            FollowUp.visit_id == v.id, FollowUp.kind == "next_visit"
        ).first()
        if exists:
            continue
        patient = db.query(Patient).filter(Patient.id == v.patient_id).first()
        if not patient or not patient.is_active or not patient.phone:
            continue

        doctor = db.query(Doctor).filter(Doctor.id == v.doctor_id).first() if v.doctor_id else None
        clinic = _clinic_name(db, v.tenant_id)
        doctor_label = _doctor_label(doctor.name if doctor else None)
        date_str = target.strftime("%A, %d %B")
        reason = (v.diagnosis or "").strip()[:60] or None
        msg = next_visit_message(patient.name, clinic, doctor_label, date_str, reason)

        delivered = _record_followup(
            db, tenant_id=v.tenant_id, branch_id=v.branch_id, kind="next_visit",
            title=f"Next-visit reminder — {patient.name}",
            notes=f"Auto reminder for the {date_str} visit.",
            due_date=due_dt, patient_id=patient.id, visit_id=v.id,
            phone=patient.phone, message=msg,
        )
        created += 1
        sent += 1 if delivered else 0
    return {"created": created, "sent": sent}


def _lead_nudges(db) -> dict:
    now = datetime.now(timezone.utc)
    newest = now - timedelta(days=settings.LEAD_NUDGE_AFTER_DAYS)
    oldest = now - timedelta(days=settings.LEAD_NUDGE_MAX_AGE_DAYS)

    leads = db.query(Lead).filter(
        Lead.status == "new",
        Lead.is_active == True,
        Lead.created_at <= newest,
        Lead.created_at >= oldest,
    ).all()

    created = sent = 0
    for lead in leads:
        # De-dup: nudge a given lead only once.
        exists = db.query(FollowUp.id).filter(
            FollowUp.lead_id == lead.id, FollowUp.kind == "lead_nudge"
        ).first()
        if exists:
            continue
        if not lead.phone:
            continue
        # Skip if this person already became a patient who booked.
        if db.query(Appointment.id).filter(
            Appointment.tenant_id == lead.tenant_id,
            Appointment.patient_phone == lead.phone,
        ).first():
            continue

        clinic = _clinic_name(db, lead.tenant_id)
        msg = lead_nudge_message(lead.name, clinic)
        delivered = _record_followup(
            db, tenant_id=lead.tenant_id, branch_id=lead.branch_id, kind="lead_nudge",
            title=f"Lead nudge — {lead.name}",
            notes="Auto nudge: enquired but hasn't booked.",
            due_date=now, lead_id=lead.id,
            phone=lead.phone, message=msg,
        )
        created += 1
        sent += 1 if delivered else 0
    return {"created": created, "sent": sent}


def run_reminders(db) -> dict:
    """Run both reminder passes. Safe to call repeatedly — de-dups itself."""
    if not settings.AUTO_REMINDERS_ENABLED:
        return {"enabled": False}
    nv = _next_visit_reminders(db)
    ln = _lead_nudges(db)
    return {
        "enabled": True,
        "next_visit": nv,
        "lead_nudge": ln,
        "created": nv["created"] + ln["created"],
        "sent": nv["sent"] + ln["sent"],
    }
