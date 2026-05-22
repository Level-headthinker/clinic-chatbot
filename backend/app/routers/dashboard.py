from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.appointment import Appointment
from app.models.branch import Branch
from app.models.chat import Lead
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.user import User
from app.services.auth import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

BOOKED_STATUSES = ("pending", "confirmed")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _start_of_day(dt: datetime) -> datetime:
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def _start_of_month(dt: datetime) -> datetime:
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


@router.get("/summary")
def dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Single endpoint that returns everything the dashboard needs in one round trip."""
    tenant_id = current_user.tenant_id
    branch_id = current_user.branch_id  # None = tenant-level; set = branch-scoped

    now = _now_utc()
    today_start = _start_of_day(now)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = _start_of_month(now)
    last_month_start = _start_of_month(now - timedelta(days=1)) if now.month > 1 else \
        now.replace(year=now.year - 1, month=12, day=1, hour=0, minute=0, second=0, microsecond=0)

    # ── Base filters ──────────────────────────────────────────
    def lead_q():
        q = db.query(Lead).filter(Lead.tenant_id == tenant_id, Lead.is_active == True)
        if branch_id:
            q = q.filter(Lead.branch_id == branch_id)
        return q

    def appt_q():
        q = db.query(Appointment).filter(Appointment.tenant_id == tenant_id, Appointment.is_active == True)
        if branch_id:
            q = q.filter(Appointment.branch_id == branch_id)
        return q

    def patient_q():
        return db.query(Patient).filter(Patient.tenant_id == tenant_id)

    def doctor_q():
        q = db.query(Doctor).filter(Doctor.tenant_id == tenant_id)
        if branch_id:
            q = q.filter(Doctor.branch_id == branch_id)
        return q

    # ── Leads ─────────────────────────────────────────────────
    lead_rows = db.query(Lead.status, func.count(Lead.id)).filter(
        Lead.tenant_id == tenant_id,
        Lead.is_active == True,
        *([Lead.branch_id == branch_id] if branch_id else []),
    ).group_by(Lead.status).all()

    lead_counts = {status: count for status, count in lead_rows}
    total_leads = sum(lead_counts.values())
    converted = lead_counts.get("converted", 0)

    leads_this_month = lead_q().filter(Lead.created_at >= month_start).count()
    leads_last_month = lead_q().filter(
        Lead.created_at >= last_month_start,
        Lead.created_at < month_start,
    ).count()

    # ── Appointments ──────────────────────────────────────────
    appt_status_rows = db.query(Appointment.status, func.count(Appointment.id)).filter(
        Appointment.tenant_id == tenant_id,
        Appointment.is_active == True,
        *([Appointment.branch_id == branch_id] if branch_id else []),
    ).group_by(Appointment.status).all()

    appt_counts = {s: c for s, c in appt_status_rows}
    total_appts = sum(appt_counts.values())

    today_appts = appt_q().filter(Appointment.slot_datetime >= today_start).count()
    week_appts = appt_q().filter(Appointment.slot_datetime >= week_start).count()

    # ── Patients ──────────────────────────────────────────────
    total_patients = patient_q().count()
    new_patients_month = patient_q().filter(Patient.created_at >= month_start).count()

    # ── Doctors ───────────────────────────────────────────────
    total_doctors = doctor_q().count()
    active_doctors = doctor_q().filter(Doctor.is_active == True).count()

    # ── Recent appointments (last 8, with doctor name) ────────
    recent = (
        appt_q()
        .options(joinedload(Appointment.doctor))
        .order_by(Appointment.created_at.desc())
        .limit(8)
        .all()
    )

    # ── Per-branch breakdown (tenant-level admins only) ───────
    branch_breakdown = []
    if branch_id is None:
        branches = db.query(Branch).filter(
            Branch.tenant_id == tenant_id,
            Branch.is_active == True,
        ).order_by(Branch.is_main_branch.desc(), Branch.name).all()

        if len(branches) > 1:
            branch_ids = [b.id for b in branches]

            b_leads = dict(
                db.query(Lead.branch_id, func.count(Lead.id))
                .filter(Lead.tenant_id == tenant_id, Lead.is_active == True, Lead.branch_id.in_(branch_ids))
                .group_by(Lead.branch_id).all()
            )
            b_appts = dict(
                db.query(Appointment.branch_id, func.count(Appointment.id))
                .filter(Appointment.tenant_id == tenant_id, Appointment.is_active == True,
                        Appointment.branch_id.in_(branch_ids))
                .group_by(Appointment.branch_id).all()
            )
            b_doctors = dict(
                db.query(Doctor.branch_id, func.count(Doctor.id))
                .filter(Doctor.tenant_id == tenant_id, Doctor.is_active == True,
                        Doctor.branch_id.in_(branch_ids))
                .group_by(Doctor.branch_id).all()
            )
            b_pending = dict(
                db.query(Appointment.branch_id, func.count(Appointment.id))
                .filter(Appointment.tenant_id == tenant_id, Appointment.is_active == True,
                        Appointment.status.in_(BOOKED_STATUSES),
                        Appointment.branch_id.in_(branch_ids))
                .group_by(Appointment.branch_id).all()
            )

            for b in branches:
                branch_breakdown.append({
                    "id": str(b.id),
                    "name": b.name,
                    "slug": b.slug,
                    "is_main_branch": b.is_main_branch,
                    "leads": b_leads.get(b.id, 0),
                    "appointments": b_appts.get(b.id, 0),
                    "pending_appointments": b_pending.get(b.id, 0),
                    "active_doctors": b_doctors.get(b.id, 0),
                })

    return {
        "leads": {
            "total": total_leads,
            "new": lead_counts.get("new", 0),
            "contacted": lead_counts.get("contacted", 0),
            "converted": converted,
            "lost": lead_counts.get("lost", 0),
            "conversion_rate": f"{(converted / total_leads * 100):.1f}%" if total_leads else "0%",
            "this_month": leads_this_month,
            "last_month": leads_last_month,
            "trend": _trend(leads_this_month, leads_last_month),
        },
        "appointments": {
            "total": total_appts,
            "today": today_appts,
            "this_week": week_appts,
            "pending": appt_counts.get("pending", 0),
            "confirmed": appt_counts.get("confirmed", 0),
            "completed": appt_counts.get("completed", 0),
            "cancelled": appt_counts.get("cancelled", 0),
            "no_show": appt_counts.get("no_show", 0),
        },
        "patients": {
            "total": total_patients,
            "new_this_month": new_patients_month,
        },
        "doctors": {
            "total": total_doctors,
            "active": active_doctors,
        },
        "recent_appointments": [
            {
                "id": str(a.id),
                "patient_name": a.patient_name,
                "patient_phone": a.patient_phone,
                "doctor_name": a.doctor.name if a.doctor else "—",
                "doctor_specialty": a.doctor.specialty if a.doctor else None,
                "slot_datetime": a.slot_datetime.isoformat() if a.slot_datetime else None,
                "status": a.status,
            }
            for a in recent
        ],
        "branches": branch_breakdown,
    }


def _trend(current: int, previous: int) -> Optional[str]:
    """Return a human-readable trend string, e.g. '+12%' or '-5%'."""
    if previous == 0:
        return "+100%" if current > 0 else "0%"
    pct = (current - previous) / previous * 100
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.0f}%"
