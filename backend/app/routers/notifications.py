from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.appointment import Appointment
from app.models.chat import Lead
from app.models.follow_up import FollowUp
from app.models.user import User
from app.services.auth import get_current_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def _now_utc():
    return datetime.now(timezone.utc)


@router.get("/")
def get_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = _now_utc()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    tenant_id = current_user.tenant_id
    branch_id = current_user.branch_id

    def branch_filter(q, model):
        if branch_id:
            return q.filter(model.branch_id == branch_id)
        return q

    # New leads (status = "new")
    new_leads_q = db.query(Lead).filter(
        Lead.tenant_id == tenant_id,
        Lead.is_active == True,
        Lead.status == "new",
    )
    new_leads_q = branch_filter(new_leads_q, Lead)
    new_leads = [
        {"id": str(l.id), "name": l.name, "phone": l.phone, "concern": l.concern}
        for l in new_leads_q.order_by(Lead.created_at.desc()).limit(10).all()
    ]

    # Today's pending/confirmed appointments
    appt_q = db.query(Appointment).options(joinedload(Appointment.doctor)).filter(
        Appointment.tenant_id == tenant_id,
        Appointment.is_active == True,
        Appointment.status.in_(["pending", "confirmed"]),
        Appointment.slot_datetime >= today_start,
        Appointment.slot_datetime < today_end,
    )
    appt_q = branch_filter(appt_q, Appointment)
    today_appointments = [
        {
            "id": str(a.id),
            "patient_name": a.patient_name,
            "patient_phone": a.patient_phone,
            "doctor_name": a.doctor.name if a.doctor else "—",
            "slot_datetime": a.slot_datetime.isoformat(),
            "status": a.status,
        }
        for a in appt_q.order_by(Appointment.slot_datetime.asc()).all()
    ]

    # Overdue + due-today follow-ups (pending)
    fu_q = db.query(FollowUp).filter(
        FollowUp.tenant_id == tenant_id,
        FollowUp.status == "pending",
        FollowUp.due_date <= today_end,
    )
    if branch_id:
        fu_q = fu_q.filter(FollowUp.branch_id == branch_id)
    due_followups = [
        {
            "id": str(f.id),
            "title": f.title,
            "due_date": f.due_date.isoformat(),
            "overdue": f.due_date < now,
        }
        for f in fu_q.order_by(FollowUp.due_date.asc()).limit(10).all()
    ]

    total = len(new_leads) + len(today_appointments) + len(due_followups)

    return {
        "total": total,
        "new_leads": new_leads,
        "today_appointments": today_appointments,
        "due_followups": due_followups,
    }
