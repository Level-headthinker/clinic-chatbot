"""APScheduler background tasks.

Runs inside the same uvicorn process. Started on app startup via lifespan.

Jobs
────
reminder_job  — runs every 30 min
    Finds appointments 23–25 hours from now with status pending/confirmed
    that haven't had a reminder sent yet, then sends a WhatsApp message.
"""
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from app.database import SessionLocal
from app.models.appointment import Appointment
from app.models.branch import Branch
from app.models.doctor import Doctor
from app.models.tenant import Tenant
from app.config import settings
from app.services.messaging import send_whatsapp, send_whatsapp_template

_scheduler = BackgroundScheduler(timezone="Asia/Karachi")


def _send_reminders():
    db = SessionLocal()
    try:
        now = datetime.now()
        window_start = now + timedelta(hours=23)
        window_end = now + timedelta(hours=25)

        appointments = db.query(Appointment).filter(
            Appointment.slot_datetime >= window_start,
            Appointment.slot_datetime <= window_end,
            Appointment.status.in_(["pending", "confirmed"]),
            Appointment.reminder_sent.is_(False),
        ).all()

        for appt in appointments:
            try:
                tenant = db.query(Tenant).filter(Tenant.id == appt.tenant_id).first()
                doctor = db.query(Doctor).filter(Doctor.id == appt.doctor_id).first()
                branch = db.query(Branch).filter(Branch.id == appt.branch_id).first()

                clinic_name = tenant.name if tenant else "the clinic"
                doctor_name = (doctor.name if doctor else "your doctor")
                if doctor_name and not doctor_name.lower().startswith("dr"):
                    doctor_name = f"Dr. {doctor_name}"

                slot_str = appt.slot_datetime.strftime("%A, %d %B at %I:%M %p")

                message = (
                    f"Hi {appt.patient_name}! 👋\n\n"
                    f"This is a reminder from {clinic_name}.\n"
                    f"Your appointment with {doctor_name} is tomorrow:\n"
                    f"📅 {slot_str}\n\n"
                    f"Please arrive 10 minutes early. "
                    f"To reschedule, reply to this message or call us directly."
                )

                # Prefer an approved template (delivers outside the 24h window),
                # fall back to free-form text (delivers within it).
                sent = False
                if settings.WA_TEMPLATE_APPT_REMINDER:
                    try:
                        sent = send_whatsapp_template(
                            appt.patient_phone, settings.WA_TEMPLATE_APPT_REMINDER,
                            settings.WA_TEMPLATE_LANG,
                            [appt.patient_name, clinic_name, doctor_name, slot_str],
                        )
                    except Exception:
                        sent = False
                if not sent:
                    sent = send_whatsapp(appt.patient_phone, message)
                if sent:
                    appt.reminder_sent = True
                    db.commit()

            except Exception:
                db.rollback()

    except Exception:
        pass
    finally:
        db.close()


def _reset_message_counters():
    """Safety net for the monthly WhatsApp limit reset. The webhook also
    self-resets on first message of a new month; this catches idle numbers."""
    from datetime import timezone
    from app.models.whatsapp_number import WhatsAppNumberMapping

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        next_month = (now.replace(day=1) + timedelta(days=32)).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        mappings = db.query(WhatsAppNumberMapping).filter(
            (WhatsAppNumberMapping.limit_reset_date.is_(None))
            | (WhatsAppNumberMapping.limit_reset_date <= now)
        ).all()
        for m in mappings:
            m.messages_used_this_month = 0
            m.limit_reset_date = next_month
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _expire_subscriptions():
    """Flip trials/periods that have ended to 'expired'."""
    from app.services.subscription_service import expire_due_subscriptions
    db = SessionLocal()
    try:
        n = expire_due_subscriptions(db)
        if n:
            print(f"⏳ {n} subscription(s) expired")
    except Exception:
        db.rollback()
    finally:
        db.close()


def _run_reminder_agent():
    """Daily: message patients before their next visit and nudge un-booked leads."""
    from app.services.reminder_agent import run_reminders
    db = SessionLocal()
    try:
        res = run_reminders(db)
        if res.get("created"):
            print(f"🔔 reminder agent: {res}")
    except Exception:
        db.rollback()
    finally:
        db.close()


def _weekly_reports():
    from app.services.reports import generate_scheduled_reports
    generate_scheduled_reports("weekly")


def _monthly_reports():
    from app.services.reports import generate_scheduled_reports
    generate_scheduled_reports("monthly")


def start_scheduler():
    """Call this once on app startup."""
    if not _scheduler.running:
        _scheduler.add_job(_send_reminders, "interval", minutes=30, id="reminder_job")
        # Monthly WhatsApp message-limit reset — 00:10 on the 1st (PKT).
        _scheduler.add_job(_reset_message_counters, "cron",
                           day=1, hour=0, minute=10, id="message_limit_reset")
        # Auto-generated clinic reports: weekly every Monday 08:00, monthly on
        # the 1st 08:00 (PKT). Exports are pre-rendered and cached for download.
        _scheduler.add_job(_weekly_reports, "cron",
                           day_of_week="mon", hour=8, minute=0, id="weekly_reports")
        _scheduler.add_job(_monthly_reports, "cron",
                           day=1, hour=8, minute=0, id="monthly_reports")
        # Expire ended trials/subscriptions — hourly is plenty.
        _scheduler.add_job(_expire_subscriptions, "interval",
                           hours=1, id="expire_subscriptions")
        # Automatic follow-up reminders — once a day at 10:00 (PKT).
        _scheduler.add_job(_run_reminder_agent, "cron",
                           hour=10, minute=0, id="reminder_agent")
        _scheduler.start()


def stop_scheduler():
    """Call this on app shutdown."""
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
