"""Clinic & platform reports API.

Clinic admin (date-range filterable, exportable):
    GET /reports/clinic?report_type=weekly&date=2026-06-08   → metrics JSON (stored)
    GET /reports/clinic/history                              → stored reports list
    GET /reports/{id}/download?format=xlsx|pdf               → branded export file

Superadmin:
    GET /super-reports/platform?report_type=monthly          → all-clinic rollup
    GET /super-reports/clinics?report_type=monthly           → per-clinic drilldown
    (downloads use the same /reports/{id}/download endpoint)
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.system_report import SystemReport
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import get_current_user, require_admin_user
from app.services.reports import (
    REPORT_TYPES,
    ensure_exports,
    generate_report,
    period_bounds,
)

router = APIRouter(prefix="/reports", tags=["Reports"])
super_router = APIRouter(prefix="/super-reports", tags=["Reports (Superadmin)"])


def _verify_super(current_user: User = Depends(get_current_user)):
    if not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user


def _parse_ref_date(date: Optional[str]) -> datetime | None:
    if not date:
        return None
    try:
        parsed = datetime.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be ISO format, e.g. 2026-06-08")
    return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc)


def _validated_type(report_type: str) -> str:
    if report_type not in REPORT_TYPES:
        raise HTTPException(status_code=400, detail=f"report_type must be one of {REPORT_TYPES}")
    return report_type


def _format_report(r: SystemReport) -> dict:
    return {
        "id": str(r.id),
        "clinic_id": str(r.clinic_id) if r.clinic_id else None,
        "report_type": r.report_type,
        "period_start": str(r.period_start),
        "period_end": str(r.period_end),
        "generated_at": str(r.generated_at),
        "metrics": r.metrics or {},
        "has_xlsx": bool(r.xlsx_path),
        "has_pdf": bool(r.pdf_path),
    }


# ── Clinic admin ───────────────────────────────────────────────────────────────

@router.get("/clinic")
def clinic_report(
    report_type: str = Query("weekly"),
    date: Optional[str] = Query(None, description="Any date inside the wanted period (ISO)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    """Generate (or reuse today's) report for the period containing `date`."""
    report_type = _validated_type(report_type)
    start, end = period_bounds(report_type, _parse_ref_date(date))
    existing = db.query(SystemReport).filter(
        SystemReport.clinic_id == current_user.tenant_id,
        SystemReport.report_type == report_type,
        SystemReport.period_start == start,
    ).order_by(SystemReport.generated_at.desc()).first()
    # Past periods are immutable → reuse. The current (incomplete) period is
    # regenerated on each request so the dashboard stays live.
    now = datetime.now(timezone.utc)
    if existing and end <= now:
        return _format_report(existing)
    if existing:
        db.delete(existing)
        db.flush()
    report = generate_report(db, current_user.tenant_id, report_type, start, end)
    return _format_report(report)


@router.get("/clinic/history")
def clinic_report_history(
    report_type: Optional[str] = Query(None),
    limit: int = Query(24, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    q = db.query(SystemReport).filter(SystemReport.clinic_id == current_user.tenant_id)
    if report_type:
        q = q.filter(SystemReport.report_type == _validated_type(report_type))
    reports = q.order_by(SystemReport.period_start.desc()).limit(limit).all()
    return [_format_report(r) for r in reports]


@router.get("/{report_id}/download")
def download_report(
    report_id: str,
    format: str = Query("pdf", pattern="^(pdf|xlsx)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    report = db.query(SystemReport).filter(SystemReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    # Tenant isolation: clinic admins may only download their own clinic's
    # reports; platform-wide reports (clinic_id NULL) are superadmin-only.
    if not current_user.is_superadmin:
        if report.clinic_id is None or report.clinic_id != current_user.tenant_id:
            raise HTTPException(status_code=403, detail="Not authorized")
    report = ensure_exports(db, report)
    path = report.pdf_path if format == "pdf" else report.xlsx_path
    media = "application/pdf" if format == "pdf" else \
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    filename = f"{report.report_type}_report_{report.period_start.strftime('%Y-%m-%d')}.{format}"
    return FileResponse(path, media_type=media, filename=filename)


# ── Superadmin ─────────────────────────────────────────────────────────────────

@super_router.get("/platform")
def platform_report(
    report_type: str = Query("monthly"),
    date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(_verify_super),
):
    report_type = _validated_type(report_type)
    start, end = period_bounds(report_type, _parse_ref_date(date))
    existing = db.query(SystemReport).filter(
        SystemReport.clinic_id.is_(None),
        SystemReport.report_type == report_type,
        SystemReport.period_start == start,
    ).order_by(SystemReport.generated_at.desc()).first()
    now = datetime.now(timezone.utc)
    if existing and end <= now:
        return _format_report(existing)
    if existing:
        db.delete(existing)
        db.flush()
    report = generate_report(db, None, report_type, start, end)
    return _format_report(report)


@super_router.get("/clinics")
def per_clinic_reports(
    report_type: str = Query("monthly"),
    date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(_verify_super),
):
    """Drill-down: the same period's report for every active clinic."""
    report_type = _validated_type(report_type)
    start, end = period_bounds(report_type, _parse_ref_date(date))
    tenants = db.query(Tenant).filter(Tenant.is_active.is_(True)).all()
    out = []
    now = datetime.now(timezone.utc)
    for tenant in tenants:
        existing = db.query(SystemReport).filter(
            SystemReport.clinic_id == tenant.id,
            SystemReport.report_type == report_type,
            SystemReport.period_start == start,
        ).order_by(SystemReport.generated_at.desc()).first()
        if existing and end <= now:
            report = existing
        else:
            if existing:
                db.delete(existing)
                db.flush()
            report = generate_report(db, tenant.id, report_type, start, end)
        item = _format_report(report)
        item["clinic_name"] = tenant.name
        out.append(item)
    return out
