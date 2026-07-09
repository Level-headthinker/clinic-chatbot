from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.appointment import Appointment
from app.models.branch import Branch
from app.models.chat import Lead
from app.models.invoice import Invoice
from app.models.patient import Patient
from app.models.user import User
from app.services.auth import get_current_user
from app.services.interaction_analytics import summarize

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/feedback")
def feedback_overview(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """The data feedback loop, made visible: the bot's conversion funnel and its
    weak spots (KB misses, output-guard interventions) for this clinic.

    Always tenant-scoped. Reads the PHI-free InteractionEvent stream — no patient
    data is exposed. Powers a "how is the AI actually doing?" dashboard card.
    """
    return summarize(db, current_user.tenant_id, days=days)


def _branch_ids_for_user(user: User, db: Session) -> list:
    """Return branch IDs the user is allowed to see."""
    if user.branch_id:
        return [user.branch_id]
    branches = db.query(Branch.id).filter(Branch.tenant_id == user.tenant_id).all()
    return [b.id for b in branches]


def _month_series(from_date: date, to_date: date):
    """Yield (year, month) tuples between two dates inclusive."""
    cur = from_date.replace(day=1)
    end = to_date.replace(day=1)
    while cur <= end:
        yield cur.year, cur.month
        if cur.month == 12:
            cur = cur.replace(year=cur.year + 1, month=1)
        else:
            cur = cur.replace(month=cur.month + 1)


@router.get("/overview")
def analytics_overview(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today = date.today()
    if not from_date:
        from_date = today.replace(day=1, month=1)  # start of current year
    if not to_date:
        to_date = today

    from_dt = datetime.combine(from_date, datetime.min.time())
    to_dt = datetime.combine(to_date, datetime.max.time())

    branch_ids = _branch_ids_for_user(current_user, db)

    # ── Load all branches the user can see ────────────────────────────────────
    branches = db.query(Branch).filter(Branch.id.in_(branch_ids)).all()
    branch_map = {b.id: b.name for b in branches}

    # ── Revenue per branch (collected = paid, billed = invoiced) ──────────────
    revenue_rows = (
        db.query(
            Invoice.branch_id,
            func.coalesce(func.sum(Invoice.paid_amount), 0),
            func.coalesce(func.sum(Invoice.total_amount), 0),
        )
        .filter(
            Invoice.branch_id.in_(branch_ids),
            Invoice.is_active == True,        # exclude soft-deleted invoices
            Invoice.created_at >= from_dt,
            Invoice.created_at <= to_dt,
        )
        .group_by(Invoice.branch_id)
        .all()
    )
    revenue_by_branch = {str(r[0]): float(r[1]) for r in revenue_rows}
    billed_by_branch = {str(r[0]): float(r[2]) for r in revenue_rows}

    # ── Appointments per branch (by status) ───────────────────────────────────
    appt_rows = (
        db.query(
            Appointment.branch_id,
            Appointment.status,
            func.count(Appointment.id),
        )
        .filter(
            Appointment.branch_id.in_(branch_ids),
            Appointment.is_active == True,    # exclude soft-deleted appointments
            Appointment.created_at >= from_dt,
            Appointment.created_at <= to_dt,
        )
        .group_by(Appointment.branch_id, Appointment.status)
        .all()
    )
    appt_by_branch: dict = {}
    for branch_id, status, count in appt_rows:
        key = str(branch_id)
        appt_by_branch.setdefault(key, {})
        appt_by_branch[key][status] = count

    # ── Leads per branch ───────────────────────────────────────────────────────
    lead_rows = (
        db.query(Lead.branch_id, Lead.status, func.count(Lead.id))
        .filter(
            Lead.branch_id.in_(branch_ids),
            Lead.is_active == True,           # exclude soft-deleted leads
            Lead.created_at >= from_dt,
            Lead.created_at <= to_dt,
        )
        .group_by(Lead.branch_id, Lead.status)
        .all()
    )
    leads_by_branch: dict = {}
    for branch_id, status, count in lead_rows:
        key = str(branch_id)
        leads_by_branch.setdefault(key, {"new": 0, "contacted": 0, "converted": 0, "lost": 0})
        leads_by_branch[key][status] = count

    # ── Patients per branch (primary_branch_id) ────────────────────────────────
    patient_rows = (
        db.query(Patient.primary_branch_id, func.count(Patient.id))
        .filter(
            Patient.primary_branch_id.in_(branch_ids),
            Patient.is_active == True,        # exclude soft-deleted patients
            Patient.created_at >= from_dt,
            Patient.created_at <= to_dt,
        )
        .group_by(Patient.primary_branch_id)
        .all()
    )
    patients_by_branch = {str(r[0]): r[1] for r in patient_rows}

    # ── Monthly revenue trend (all branches combined) ─────────────────────────
    monthly_revenue_rows = (
        db.query(
            func.date_trunc("month", Invoice.created_at).label("month"),
            func.coalesce(func.sum(Invoice.paid_amount), 0),
        )
        .filter(
            Invoice.branch_id.in_(branch_ids),
            Invoice.is_active == True,
            Invoice.created_at >= from_dt,
            Invoice.created_at <= to_dt,
        )
        .group_by("month")
        .order_by("month")
        .all()
    )
    monthly_revenue_map = {
        (r[0].year, r[0].month): float(r[1]) for r in monthly_revenue_rows
    }

    # ── Monthly leads trend ────────────────────────────────────────────────────
    monthly_leads_rows = (
        db.query(
            func.date_trunc("month", Lead.created_at).label("month"),
            func.count(Lead.id),
        )
        .filter(
            Lead.branch_id.in_(branch_ids),
            Lead.is_active == True,
            Lead.created_at >= from_dt,
            Lead.created_at <= to_dt,
        )
        .group_by("month")
        .order_by("month")
        .all()
    )
    monthly_leads_map = {
        (r[0].year, r[0].month): r[1] for r in monthly_leads_rows
    }

    # Fill in every month in the range (zero for months with no data)
    trend = []
    for y, m in _month_series(from_date, to_date):
        trend.append({
            "month": f"{y}-{m:02d}",
            "revenue": monthly_revenue_map.get((y, m), 0),
            "leads": monthly_leads_map.get((y, m), 0),
        })

    # ── Assemble per-branch summary ────────────────────────────────────────────
    branch_summaries = []
    total_collected = 0.0
    total_billed = 0.0
    total_patients = 0
    total_leads = 0
    total_converted = 0
    total_appts = 0
    total_completed = 0
    total_no_show = 0

    for branch in branches:
        bid = str(branch.id)
        rev = revenue_by_branch.get(bid, 0.0)
        billed = billed_by_branch.get(bid, 0.0)
        appts = appt_by_branch.get(bid, {})
        leads_data = leads_by_branch.get(bid, {"new": 0, "contacted": 0, "converted": 0, "lost": 0})
        patients = patients_by_branch.get(bid, 0)

        branch_leads = sum(leads_data.values())
        branch_converted = leads_data.get("converted", 0)
        # Count every appointment, whatever its status (don't drop no_show etc.)
        appts_total = sum(appts.values())
        completed = appts.get("completed", 0)
        no_show = appts.get("no_show", 0)

        total_collected += rev
        total_billed += billed
        total_patients += patients
        total_leads += branch_leads
        total_converted += branch_converted
        total_appts += appts_total
        total_completed += completed
        total_no_show += no_show

        branch_summaries.append({
            "branch_id": bid,
            "branch_name": branch.name,
            "revenue": rev,                      # collected (kept for compatibility)
            "collected": rev,
            "billed": billed,
            "outstanding": max(billed - rev, 0),
            "patients": patients,
            "leads": branch_leads,
            "leads_converted": branch_converted,
            "conversion_rate": round(branch_converted / branch_leads * 100) if branch_leads else 0,
            "appointments": {
                "pending": appts.get("pending", 0),
                "confirmed": appts.get("confirmed", 0),
                "checked_in": appts.get("checked_in", 0),
                "in_progress": appts.get("in_progress", 0),
                "completed": completed,
                "cancelled": appts.get("cancelled", 0),
                "no_show": no_show,
                "total": appts_total,
            },
        })

    # Sort by revenue (collected) descending
    branch_summaries.sort(key=lambda x: x["revenue"], reverse=True)

    return {
        "from_date": str(from_date),
        "to_date": str(to_date),
        "totals": {
            "revenue": total_collected,          # collected (kept for compatibility)
            "collected": total_collected,
            "billed": total_billed,
            "outstanding": max(total_billed - total_collected, 0),
            "collection_rate": round(total_collected / total_billed * 100) if total_billed else 0,
            "patients": total_patients,
            "leads": total_leads,
            "leads_converted": total_converted,
            "conversion_rate": round(total_converted / total_leads * 100) if total_leads else 0,
            "appointments": total_appts,
            "appointments_completed": total_completed,
            "appointments_no_show": total_no_show,
            "completion_rate": round(total_completed / total_appts * 100) if total_appts else 0,
        },
        "branches": branch_summaries,
        "trend": trend,
    }
