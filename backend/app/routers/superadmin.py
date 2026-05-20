from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.models.doctor import Doctor
from app.models.appointment import Appointment
from app.models.chat import Lead, ChatSession
from app.models.flagged_log import FlaggedLog
from app.services.auth import get_current_user
from app.services.conversation_logger import flag_type_label

router = APIRouter(prefix="/super", tags=["Super Admin"])


def verify_super_admin(current_user: User = Depends(get_current_user)):
    if not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user


# ════════════════════════════════════════════════════════════
# EXISTING ENDPOINTS (unchanged)
# ════════════════════════════════════════════════════════════

@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_super_admin)
):
    total_tenants = db.query(Tenant).filter(Tenant.is_active == True).count()
    total_appointments = db.query(Appointment).count()
    total_leads = db.query(Lead).count()
    total_doctors = db.query(Doctor).filter(Doctor.is_active == True).count()
    total_chats = db.query(ChatSession).count()
    total_flags = db.query(FlaggedLog).count()
    critical_flags = db.query(FlaggedLog).filter(
        FlaggedLog.flag_type.in_([
            "injection", "role_override", "jailbreak",
            "data_extraction", "sql_injection", "patient_leak"
        ])
    ).count()

    return {
        "total_clinics": total_tenants,
        "total_appointments": total_appointments,
        "total_leads": total_leads,
        "total_doctors": total_doctors,
        "total_chats": total_chats,
        "total_flags": total_flags,
        "critical_flags": critical_flags,
        "estimated_mrr": total_tenants * 3000,
        "estimated_arr": total_tenants * 3000 * 12,
    }


@router.get("/clinics")
def get_all_clinics(
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_super_admin)
):
    tenants = db.query(Tenant).order_by(Tenant.created_at.desc()).all()

    appointment_counts = dict(
        db.query(Appointment.tenant_id, func.count(Appointment.id))
        .group_by(Appointment.tenant_id).all()
    )
    lead_counts = dict(
        db.query(Lead.tenant_id, func.count(Lead.id))
        .group_by(Lead.tenant_id).all()
    )
    doctor_counts = dict(
        db.query(Doctor.tenant_id, func.count(Doctor.id))
        .filter(Doctor.is_active == True)
        .group_by(Doctor.tenant_id).all()
    )
    chat_counts = dict(
        db.query(ChatSession.tenant_id, func.count(ChatSession.id))
        .group_by(ChatSession.tenant_id).all()
    )
    flag_counts = dict(
        db.query(FlaggedLog.tenant_id, func.count(FlaggedLog.id))
        .group_by(FlaggedLog.tenant_id).all()
    )

    result = []
    for t in tenants:
        result.append({
            "id": str(t.id),
            "name": t.name,
            "slug": t.slug,
            "plan": t.plan,
            "is_active": t.is_active,
            "created_at": str(t.created_at),
            "appointments": appointment_counts.get(t.id, 0),
            "leads": lead_counts.get(t.id, 0),
            "doctors": doctor_counts.get(t.id, 0),
            "chats": chat_counts.get(t.id, 0),
            "security_flags": flag_counts.get(t.id, 0),
        })
    return result


@router.put("/clinics/{tenant_id}/toggle")
def toggle_clinic(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_super_admin)
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Clinic not found")
    tenant.is_active = not tenant.is_active
    db.commit()
    return {
        "message": f"Clinic {'activated' if tenant.is_active else 'deactivated'}",
        "is_active": tenant.is_active
    }


@router.put("/clinics/{tenant_id}/plan")
def update_plan(
    tenant_id: str,
    plan: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_super_admin)
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Clinic not found")
    allowed = ["starter", "growth", "enterprise"]
    if plan not in allowed:
        raise HTTPException(status_code=400, detail=f"Plan must be one of {allowed}")
    tenant.plan = plan
    db.commit()
    return {"message": "Plan updated", "plan": plan}


# ════════════════════════════════════════════════════════════
# PHASE 4 — SECURITY FLAG ENDPOINTS (superadmin: all clinics)
# ════════════════════════════════════════════════════════════

@router.get("/security/stats")
def security_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_super_admin)
):
    """
    Platform-wide breakdown of flag types and sources.
    Use this to spot trends — e.g. one clinic getting
    hammered with injection attempts.
    """
    # Count by flag type
    by_type = db.query(
        FlaggedLog.flag_type,
        func.count(FlaggedLog.id).label("count")
    ).group_by(FlaggedLog.flag_type).all()

    # Count by source
    by_source = db.query(
        FlaggedLog.source,
        func.count(FlaggedLog.id).label("count")
    ).group_by(FlaggedLog.source).all()

    # Count unreviewed
    unreviewed = db.query(FlaggedLog).filter(
        FlaggedLog.reviewed == False
    ).count()

    # Most targeted clinics
    by_clinic = db.query(
        FlaggedLog.tenant_id,
        func.count(FlaggedLog.id).label("count")
    ).filter(
        FlaggedLog.tenant_id != None
    ).group_by(FlaggedLog.tenant_id).order_by(
        func.count(FlaggedLog.id).desc()
    ).limit(5).all()

    # Resolve tenant names
    clinic_ids = [str(row[0]) for row in by_clinic]
    tenants = {
        str(t.id): t.name
        for t in db.query(Tenant).filter(Tenant.id.in_(clinic_ids)).all()
    }

    return {
        "total_flags": sum(row[1] for row in by_type),
        "unreviewed": unreviewed,
        "by_type": [
            {
                "flag_type": row[0],
                "label": flag_type_label(row[0]),
                "count": row[1]
            }
            for row in sorted(by_type, key=lambda x: -x[1])
        ],
        "by_source": [
            {"source": row[0], "count": row[1]}
            for row in by_source
        ],
        "most_targeted_clinics": [
            {
                "tenant_id": str(row[0]),
                "clinic_name": tenants.get(str(row[0]), "Unknown"),
                "flag_count": row[1]
            }
            for row in by_clinic
        ]
    }


@router.get("/security/flags")
def list_all_flags(
    flag_type: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    reviewed: Optional[bool] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_super_admin)
):
    """
    List all flagged events across all clinics.
    Filterable by flag_type, source, clinic, reviewed status.
    """
    query = db.query(FlaggedLog)

    if flag_type:
        query = query.filter(FlaggedLog.flag_type == flag_type)
    if source:
        query = query.filter(FlaggedLog.source == source)
    if tenant_id:
        query = query.filter(FlaggedLog.tenant_id == tenant_id)
    if reviewed is not None:
        query = query.filter(FlaggedLog.reviewed == reviewed)

    total = query.count()
    flags = query.order_by(FlaggedLog.created_at.desc()).offset(offset).limit(limit).all()

    # Resolve tenant names in one query
    tenant_ids = list({str(f.tenant_id) for f in flags if f.tenant_id})
    tenants = {
        str(t.id): t.name
        for t in db.query(Tenant).filter(Tenant.id.in_(tenant_ids)).all()
    }

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "flags": [_format_flag(f, tenants) for f in flags]
    }


@router.put("/security/flags/{flag_id}/review")
def mark_reviewed(
    flag_id: str,
    note: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_super_admin)
):
    """Mark a flag as reviewed after a human has looked at it."""
    flag = db.query(FlaggedLog).filter(FlaggedLog.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    flag.reviewed = True
    flag.reviewed_note = note
    db.commit()
    return {"message": "Marked as reviewed"}


@router.delete("/security/flags/clear-reviewed")
def clear_reviewed_flags(
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_super_admin)
):
    """Delete all reviewed flags to keep the table clean."""
    deleted = db.query(FlaggedLog).filter(FlaggedLog.reviewed == True).delete()
    db.commit()
    return {"message": f"Deleted {deleted} reviewed flags"}


# ════════════════════════════════════════════════════════════
# CLINIC ADMIN — own clinic's flags only
# ════════════════════════════════════════════════════════════

@router.get("/my-clinic/security/flags")
def my_clinic_flags(
    flag_type: Optional[str] = Query(None),
    reviewed: Optional[bool] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)   # any admin, not just superadmin
):
    """
    Clinic admins can see flags for their own clinic only.
    Superadmin can use /super/security/flags to see all.
    """
    query = db.query(FlaggedLog).filter(
        FlaggedLog.tenant_id == current_user.tenant_id
    )
    if flag_type:
        query = query.filter(FlaggedLog.flag_type == flag_type)
    if reviewed is not None:
        query = query.filter(FlaggedLog.reviewed == reviewed)

    total = query.count()
    flags = query.order_by(FlaggedLog.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "flags": [_format_flag(f, {}) for f in flags]
    }


@router.get("/my-clinic/security/stats")
def my_clinic_security_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Security summary for the logged-in clinic's admin dashboard."""
    by_type = db.query(
        FlaggedLog.flag_type,
        func.count(FlaggedLog.id).label("count")
    ).filter(
        FlaggedLog.tenant_id == current_user.tenant_id
    ).group_by(FlaggedLog.flag_type).all()

    unreviewed = db.query(FlaggedLog).filter(
        FlaggedLog.tenant_id == current_user.tenant_id,
        FlaggedLog.reviewed == False
    ).count()

    total = sum(row[1] for row in by_type)

    return {
        "total_flags": total,
        "unreviewed": unreviewed,
        "by_type": [
            {
                "flag_type": row[0],
                "label": flag_type_label(row[0]),
                "count": row[1]
            }
            for row in sorted(by_type, key=lambda x: -x[1])
        ]
    }


# ════════════════════════════════════════════════════════════
# SHARED FORMATTER
# ════════════════════════════════════════════════════════════

def _format_flag(flag: FlaggedLog, tenants: dict) -> dict:
    return {
        "id": str(flag.id),
        "flag_type": flag.flag_type,
        "label": flag_type_label(flag.flag_type),
        "source": flag.source,
        "clinic_name": tenants.get(str(flag.tenant_id), "Unknown") if flag.tenant_id else "Pre-session",
        "tenant_id": str(flag.tenant_id) if flag.tenant_id else None,
        "session_token": flag.session_token,
        "flagged_message": flag.flagged_message,
        "intercepted_response": flag.intercepted_response,
        "safe_response": flag.safe_response,
        "blocked_reason": flag.blocked_reason,
        "reviewed": flag.reviewed,
        "reviewed_note": flag.reviewed_note,
        "created_at": str(flag.created_at),
    }