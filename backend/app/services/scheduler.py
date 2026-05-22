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
from app.services.messaging import send_whatsapp

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


def start_scheduler():
    """Call this once on app startup."""
    if not _scheduler.running:
        _scheduler.add_job(_send_reminders, "interval", minutes=30, id="reminder_job")
        _scheduler.start()


def stop_scheduler():
    """Call this on app shutdown."""
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
