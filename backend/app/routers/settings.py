from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.branch import Branch
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import get_current_user

router = APIRouter(prefix="/settings", tags=["Settings"])


_ALLOWED_TONES = {"warm", "formal", "casual", "professional", "concise"}


class ClinicSettings(BaseModel):
    clinic_name: Optional[str] = None
    bot_name: Optional[str] = None
    welcome_message: Optional[str] = None
    primary_color: Optional[str] = None
    bot_tone: Optional[str] = None
    # Branch-level overrides (for the user's main branch)
    branch_bot_name: Optional[str] = None
    branch_welcome_message: Optional[str] = None
    branch_address: Optional[str] = None
    branch_city: Optional[str] = None
    branch_phone: Optional[str] = None
    branch_timezone: Optional[str] = None
    branch_working_hours: Optional[str] = None


@router.get("")
def get_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Clinic not found")

    # Resolve branch
    if current_user.branch_id:
        branch = db.query(Branch).filter(Branch.id == current_user.branch_id).first()
    else:
        branch = db.query(Branch).filter(
            Branch.tenant_id == tenant.id,
            Branch.is_main_branch == True,
        ).first()

    return {
        "clinic_name": tenant.name,
        "bot_name": tenant.bot_name,
        "welcome_message": tenant.welcome_message,
        "primary_color": tenant.primary_color,
        "bot_tone": tenant.bot_tone or "warm",
        "branch_bot_name": branch.bot_name if branch else None,
        "branch_welcome_message": branch.welcome_message if branch else None,
        "branch_address": branch.address if branch else None,
        "branch_city": branch.city if branch else None,
        "branch_phone": branch.phone if branch else None,
        "branch_timezone": branch.timezone if branch else "Asia/Karachi",
        "branch_slug": branch.slug if branch else None,
        "branch_working_hours": branch.working_hours if branch else None,
    }


@router.put("")
def update_settings(
    data: ClinicSettings,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Clinic not found")

    # Only tenant-level admins can update clinic name / global bot settings
    if current_user.branch_id is None:
        if data.clinic_name is not None:
            tenant.name = data.clinic_name.strip()
        if data.bot_name is not None:
            tenant.bot_name = data.bot_name.strip()
        if data.welcome_message is not None:
            tenant.welcome_message = data.welcome_message.strip()
        if data.primary_color is not None:
            tenant.primary_color = data.primary_color
        if data.bot_tone is not None:
            tone = data.bot_tone.strip().lower()
            if tone not in _ALLOWED_TONES:
                raise HTTPException(status_code=400, detail=f"Tone must be one of {sorted(_ALLOWED_TONES)}")
            tenant.bot_tone = tone

    # Branch settings (all admins can update their own branch)
    if current_user.branch_id:
        branch = db.query(Branch).filter(Branch.id == current_user.branch_id).first()
    else:
        branch = db.query(Branch).filter(
            Branch.tenant_id == tenant.id,
            Branch.is_main_branch == True,
        ).first()

    if branch:
        if data.branch_bot_name is not None:
            branch.bot_name = data.branch_bot_name.strip() or None
        if data.branch_welcome_message is not None:
            branch.welcome_message = data.branch_welcome_message.strip() or None
        if data.branch_address is not None:
            branch.address = data.branch_address.strip() or None
        if data.branch_city is not None:
            branch.city = data.branch_city.strip() or None
        if data.branch_phone is not None:
            branch.phone = data.branch_phone.strip() or None
        if data.branch_timezone is not None:
            branch.timezone = data.branch_timezone or "Asia/Karachi"
        if data.branch_working_hours is not None:
            branch.working_hours = data.branch_working_hours.strip() or None

    db.commit()
    return {"message": "Settings saved."}
