"""Getting-started wizard status.

A new clinic lands on an empty dashboard — this drives a guided checklist so they
know exactly what to set up before their bot can work. Step completion is derived
LIVE from the data (no flags to keep in sync); only the "dismissed" preference is
stored on the tenant so the wizard stops nagging once they finish or skip it.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.branch import Branch
from app.models.doctor import Doctor
from app.models.tenant import Tenant
from app.models.user import User
from app.models.whatsapp_number import WhatsAppNumberMapping
from app.services.auth import require_admin_user

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])

# Default strings from sign-up — treat these as "not customised yet".
_DEFAULT_WELCOME = "Hello! How can I help you today?"


def _main_branch(db: Session, tenant_id):
    return (
        db.query(Branch)
        .filter(Branch.tenant_id == tenant_id, Branch.is_active == True)
        .order_by(Branch.is_main_branch.desc())
        .first()
    )


@router.get("/status")
def onboarding_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    branch = _main_branch(db, current_user.tenant_id)

    profile_done = bool(
        tenant and tenant.welcome_message
        and tenant.welcome_message.strip()
        and tenant.welcome_message.strip() != _DEFAULT_WELCOME
    )
    branch_done = bool(
        branch and branch.working_hours and branch.working_hours.strip()
        and (branch.address or branch.city or branch.phone)
    )
    doctors_done = (
        db.query(Doctor)
        .filter(Doctor.tenant_id == current_user.tenant_id, Doctor.is_active == True)
        .count() > 0
    )
    whatsapp_done = (
        db.query(WhatsAppNumberMapping)
        .filter(WhatsAppNumberMapping.tenant_id == current_user.tenant_id)
        .count() > 0
    )

    steps = [
        {"key": "profile", "label": "Personalise your bot",
         "desc": "Set your welcome message, tone and branding.",
         "done": profile_done, "required": True, "path": "/settings"},
        {"key": "branch", "label": "Add clinic details",
         "desc": "Address, phone and working hours so the bot can answer patients.",
         "done": branch_done, "required": True, "path": "/settings"},
        {"key": "doctors", "label": "Add your doctors",
         "desc": "At least one doctor with timings — required before the bot can book.",
         "done": doctors_done, "required": True, "path": "/doctors"},
        {"key": "whatsapp", "label": "Connect WhatsApp",
         "desc": "Link your WhatsApp number so patients can chat the bot.",
         "done": whatsapp_done, "required": False, "path": "/settings"},
        {"key": "test", "label": "Try your bot",
         "desc": "Open the live preview and send it a message.",
         "done": False, "required": False, "path": "/chat-preview"},
    ]

    required_done = sum(1 for s in steps if s["required"] and s["done"])
    required_total = sum(1 for s in steps if s["required"])
    completed = required_done == required_total

    return {
        "steps": steps,
        "completed_required": required_done,
        "total_required": required_total,
        "completed": completed,
        "dismissed": bool(tenant and tenant.onboarding_dismissed),
    }


@router.post("/dismiss")
def dismiss_onboarding(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    """Hide the getting-started wizard (finished or skipped)."""
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if tenant:
        tenant.onboarding_dismissed = True
        db.commit()
    return {"dismissed": True}
