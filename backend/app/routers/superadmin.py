from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.models.branch import Branch
from app.models.tenant import Tenant
from app.models.user import User
from app.models.doctor import Doctor
from app.models.appointment import Appointment
from app.models.chat import Lead, ChatSession
import httpx

from app.config import settings
from app.models.flagged_log import FlaggedLog
from app.models.whatsapp_number import WhatsAppNumberMapping
from app.services.auth import get_current_user, require_admin_user
from app.services.conversation_logger import flag_type_label
from pydantic import BaseModel, Field

_META_API_BASE = "https://graph.facebook.com/v19.0"

router = APIRouter(prefix="/super", tags=["Super Admin"])


def verify_super_admin(current_user: User = Depends(get_current_user)):
    if not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user


# ════════════════════════════════════════════════════════════
# EXISTING ENDPOINTS (unchanged)
# ════════════════════════════════════════════════════════════

@router.get("/feedback")
def feedback_rollup(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_super_admin),
):
    """Platform-wide data feedback loop: global funnel + per-clinic rollup,
    including the safety (output-guard) rate that stays out of the per-clinic
    admin view. Superadmin only. PHI-free (reads InteractionEvent)."""
    from app.services.interaction_analytics import summarize_global
    return summarize_global(db, days=days)


@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_super_admin)
):
    total_tenants = db.query(Tenant).filter(Tenant.is_active == True).count()
    total_branches = db.query(Branch).filter(Branch.is_active == True).count()
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
        "total_branches": total_branches,
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
    branch_counts = dict(
        db.query(Branch.tenant_id, func.count(Branch.id))
        .filter(Branch.is_active == True)
        .group_by(Branch.tenant_id).all()
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
            "branches": branch_counts.get(t.id, 0),
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


@router.get("/clinics/{tenant_id}/branches")
def get_clinic_branches(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_super_admin),
):
    """List all branches for a clinic with per-branch stats."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Clinic not found")

    branches = db.query(Branch).filter(
        Branch.tenant_id == tenant_id
    ).order_by(Branch.is_main_branch.desc(), Branch.name).all()

    if not branches:
        return []

    branch_ids = [b.id for b in branches]

    appt_counts = dict(
        db.query(Appointment.branch_id, func.count(Appointment.id))
        .filter(Appointment.tenant_id == tenant_id, Appointment.branch_id.in_(branch_ids))
        .group_by(Appointment.branch_id).all()
    )
    lead_counts = dict(
        db.query(Lead.branch_id, func.count(Lead.id))
        .filter(Lead.tenant_id == tenant_id, Lead.branch_id.in_(branch_ids))
        .group_by(Lead.branch_id).all()
    )
    doctor_counts = dict(
        db.query(Doctor.branch_id, func.count(Doctor.id))
        .filter(Doctor.tenant_id == tenant_id, Doctor.is_active == True, Doctor.branch_id.in_(branch_ids))
        .group_by(Doctor.branch_id).all()
    )
    chat_counts = dict(
        db.query(ChatSession.branch_id, func.count(ChatSession.id))
        .filter(ChatSession.tenant_id == tenant_id, ChatSession.branch_id.in_(branch_ids))
        .group_by(ChatSession.branch_id).all()
    )

    return [
        {
            "id": str(b.id),
            "name": b.name,
            "slug": b.slug,
            "city": b.city,
            "is_main_branch": b.is_main_branch,
            "is_active": b.is_active,
            "created_at": str(b.created_at),
            "appointments": appt_counts.get(b.id, 0),
            "leads": lead_counts.get(b.id, 0),
            "active_doctors": doctor_counts.get(b.id, 0),
            "chat_sessions": chat_counts.get(b.id, 0),
        }
        for b in branches
    ]


@router.put("/clinics/{tenant_id}/branches/{branch_id}/toggle")
def toggle_branch(
    tenant_id: str,
    branch_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_super_admin),
):
    """Activate or deactivate a branch."""
    branch = db.query(Branch).filter(
        Branch.id == branch_id,
        Branch.tenant_id == tenant_id,
    ).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    if branch.is_active:
        active_count = db.query(Branch).filter(
            Branch.tenant_id == tenant_id,
            Branch.is_active == True,
        ).count()
        if active_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot deactivate the last active branch")

    branch.is_active = not branch.is_active
    db.commit()
    return {"is_active": branch.is_active, "name": branch.name}


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
# WHATSAPP NUMBER MAPPINGS — phone_number_id → clinic routing
# ════════════════════════════════════════════════════════════

class NumberMappingIn(BaseModel):
    tenant_id: str
    branch_id: Optional[str] = None
    phone_number_id: str = Field(min_length=1, max_length=64)
    whatsapp_number: str = Field(default="", max_length=32)
    message_limit_monthly: int = Field(default=1000, ge=0)


@router.get("/whatsapp/numbers")
def list_number_mappings(
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_super_admin),
):
    """All registered WhatsApp numbers, who owns them, and monthly usage."""
    mappings = db.query(WhatsAppNumberMapping).order_by(
        WhatsAppNumberMapping.created_at.desc()
    ).all()
    tenant_names = {
        str(t.id): t.name
        for t in db.query(Tenant).filter(
            Tenant.id.in_([m.tenant_id for m in mappings])
        ).all()
    } if mappings else {}
    return [
        {
            "id": str(m.id),
            "tenant_id": str(m.tenant_id),
            "clinic_name": tenant_names.get(str(m.tenant_id), "Unknown"),
            "branch_id": str(m.branch_id) if m.branch_id else None,
            "phone_number_id": m.phone_number_id,
            "whatsapp_number": m.whatsapp_number,
            "is_active": m.is_active,
            "limit": m.message_limit_monthly,
            "used": m.messages_used_this_month,
            "resets_at": str(m.limit_reset_date) if m.limit_reset_date else None,
        }
        for m in mappings
    ]


@router.post("/whatsapp/numbers")
def register_number_mapping(
    data: NumberMappingIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_super_admin),
):
    """Register a clinic's WhatsApp number (Meta phone_number_id → clinic)."""
    tenant = db.query(Tenant).filter(Tenant.id == data.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Clinic not found")
    if data.branch_id:
        branch = db.query(Branch).filter(
            Branch.id == data.branch_id, Branch.tenant_id == tenant.id
        ).first()
        if not branch:
            raise HTTPException(status_code=404, detail="Branch not found in that clinic")
    existing = db.query(WhatsAppNumberMapping).filter(
        WhatsAppNumberMapping.phone_number_id == data.phone_number_id
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="phone_number_id already registered")
    mapping = WhatsAppNumberMapping(
        tenant_id=data.tenant_id,
        branch_id=data.branch_id,
        phone_number_id=data.phone_number_id,
        whatsapp_number=data.whatsapp_number,
        message_limit_monthly=data.message_limit_monthly,
    )
    db.add(mapping)
    db.commit()
    return {"id": str(mapping.id), "message": "Number registered"}


class ConnectWhatsAppIn(BaseModel):
    tenant_id: str
    branch_id: Optional[str] = None
    phone_number_id: str = Field(min_length=1, max_length=64)
    whatsapp_number: str = Field(default="", max_length=32)
    waba_id: Optional[str] = None              # to auto-subscribe the webhook
    register_pin: Optional[str] = None          # 6-digit PIN to register the number
    message_limit_monthly: int = Field(default=1000, ge=0)


def _graph_post(path: str, json_body: dict) -> tuple[bool, str]:
    """One Graph API POST with the platform access token. Never raises."""
    if not settings.META_ACCESS_TOKEN:
        return False, "META_ACCESS_TOKEN not set"
    try:
        resp = httpx.post(
            f"{_META_API_BASE}/{path}",
            headers={"Authorization": f"Bearer {settings.META_ACCESS_TOKEN}"},
            json=json_body,
            timeout=15,
        )
        if resp.status_code in (200, 201):
            return True, "ok"
        return False, f"{resp.status_code}: {resp.text[:300]}"
    except Exception as e:  # noqa: BLE001
        return False, str(e)


@router.post("/whatsapp/connect")
def connect_whatsapp(
    data: ConnectWhatsAppIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_super_admin),
):
    """One-click connect: subscribe the WABA to our webhook, register the number
    for the Cloud API, and create the phone_number_id -> clinic routing mapping.

    Each Graph API step is attempted and its status reported, but the routing
    MAPPING is always created — so the number works for receive/reply even if a
    Graph automation step is skipped (e.g. already registered, or no waba_id).
    """
    tenant = db.query(Tenant).filter(Tenant.id == data.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Clinic not found")
    if data.branch_id:
        branch = db.query(Branch).filter(
            Branch.id == data.branch_id, Branch.tenant_id == tenant.id
        ).first()
        if not branch:
            raise HTTPException(status_code=404, detail="Branch not found in that clinic")

    steps = []

    # 1 — subscribe our app to the clinic's WABA (so webhooks flow). Optional.
    if data.waba_id:
        ok, detail = _graph_post(f"{data.waba_id}/subscribed_apps", {})
        steps.append({"step": "subscribe_app", "ok": ok, "detail": detail})
    else:
        steps.append({"step": "subscribe_app", "ok": None,
                      "detail": "skipped — no waba_id (fine if the number is in your own WABA)"})

    # 2 — register the number for the Cloud API. Needs a 6-digit PIN. Optional.
    if data.register_pin:
        ok, detail = _graph_post(
            f"{data.phone_number_id}/register",
            {"messaging_product": "whatsapp", "pin": data.register_pin},
        )
        # "already registered" is a success for our purposes.
        if not ok and "already" in detail.lower():
            ok, detail = True, "already registered"
        steps.append({"step": "register_number", "ok": ok, "detail": detail})
    else:
        steps.append({"step": "register_number", "ok": None,
                      "detail": "skipped — no PIN (register once in Meta if not done)"})

    # 3 — create/update the routing mapping (this is what makes routing work).
    mapping = db.query(WhatsAppNumberMapping).filter(
        WhatsAppNumberMapping.phone_number_id == data.phone_number_id
    ).first()
    if mapping:
        mapping.tenant_id = data.tenant_id
        mapping.branch_id = data.branch_id
        mapping.whatsapp_number = data.whatsapp_number or mapping.whatsapp_number
        mapping.message_limit_monthly = data.message_limit_monthly
        mapping.is_active = True
        steps.append({"step": "mapping", "ok": True, "detail": "updated"})
    else:
        mapping = WhatsAppNumberMapping(
            tenant_id=data.tenant_id, branch_id=data.branch_id,
            phone_number_id=data.phone_number_id,
            whatsapp_number=data.whatsapp_number,
            message_limit_monthly=data.message_limit_monthly,
        )
        db.add(mapping)
        steps.append({"step": "mapping", "ok": True, "detail": "created"})
    db.commit()
    db.refresh(mapping)

    return {
        "mapping_id": str(mapping.id),
        "connected": True,
        "steps": steps,
        "note": "The number now routes to this clinic. Send it a WhatsApp to test.",
    }


@router.put("/whatsapp/numbers/{mapping_id}/limit")
def set_message_limit(
    mapping_id: str,
    limit: int = Query(ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_super_admin),
):
    mapping = db.query(WhatsAppNumberMapping).filter(
        WhatsAppNumberMapping.id == mapping_id
    ).first()
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")
    mapping.message_limit_monthly = limit
    db.commit()
    return {"message": "Limit updated", "limit": limit}


@router.put("/whatsapp/numbers/{mapping_id}/toggle")
def toggle_number_mapping(
    mapping_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_super_admin),
):
    mapping = db.query(WhatsAppNumberMapping).filter(
        WhatsAppNumberMapping.id == mapping_id
    ).first()
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")
    mapping.is_active = not mapping.is_active
    db.commit()
    return {"is_active": mapping.is_active}


@router.get("/clinics/{tenant_id}/message-stats")
def clinic_message_stats(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_super_admin),
):
    """Per-clinic WhatsApp usage vs limit (all their numbers)."""
    mappings = db.query(WhatsAppNumberMapping).filter(
        WhatsAppNumberMapping.tenant_id == tenant_id
    ).all()
    return {
        "tenant_id": tenant_id,
        "numbers": [
            {
                "phone_number_id": m.phone_number_id,
                "whatsapp_number": m.whatsapp_number,
                "is_active": m.is_active,
                "limit": m.message_limit_monthly,
                "used": m.messages_used_this_month,
                "remaining": max(0, m.message_limit_monthly - m.messages_used_this_month),
            }
            for m in mappings
        ],
        "total_used": sum(m.messages_used_this_month for m in mappings),
        "total_limit": sum(m.message_limit_monthly for m in mappings),
    }


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
    current_user: User = Depends(require_admin_user)   # clinic admins, not plain staff
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
    current_user: User = Depends(require_admin_user)
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