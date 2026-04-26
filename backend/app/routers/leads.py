# Manages leads captured by the chatbot.
# Admin can view all leads, update their status, and add notes for follow-up tracking.

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models.chat import Lead
from app.models.user import User
from app.services.auth import get_current_user

router = APIRouter(prefix="/leads", tags=["Leads"])


class LeadUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


@router.get("/")
def list_leads(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Lead).filter(
        Lead.tenant_id == current_user.tenant_id,
        Lead.is_active == True
    )
    if status:
        query = query.filter(Lead.status == status)

    leads = query.order_by(Lead.created_at.desc()).all()

    return [
        {
            "id": str(l.id),
            "name": l.name,
            "phone": l.phone,
            "concern": l.concern,
            "status": l.status,
            "source": l.source,
            "created_at": str(l.created_at)
        }
        for l in leads
    ]


@router.put("/{lead_id}")
def update_lead(
    lead_id: str,
    data: LeadUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.tenant_id == current_user.tenant_id
    ).first()
    if not lead:
        raise HTTPException(
            status_code=404,
            detail="Lead not found"
        )

    if data.status is not None:
        allowed = ["new", "contacted", "converted", "lost"]
        if data.status not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Status must be one of {allowed}"
            )
        lead.status = data.status

    db.commit()
    return {"message": "Lead updated successfully"}


@router.delete("/{lead_id}")
def delete_lead(
    lead_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.tenant_id == current_user.tenant_id
    ).first()
    if not lead:
        raise HTTPException(
            status_code=404,
            detail="Lead not found"
        )

    lead.is_active = False
    db.commit()
    return {"message": "Lead removed"}


@router.get("/stats")
def lead_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    total = db.query(Lead).filter(
        Lead.tenant_id == current_user.tenant_id
    ).count()
    new = db.query(Lead).filter(
        Lead.tenant_id == current_user.tenant_id,
        Lead.status == "new"
    ).count()
    contacted = db.query(Lead).filter(
        Lead.tenant_id == current_user.tenant_id,
        Lead.status == "contacted"
    ).count()
    converted = db.query(Lead).filter(
        Lead.tenant_id == current_user.tenant_id,
        Lead.status == "converted"
    ).count()

    return {
        "total": total,
        "new": new,
        "contacted": contacted,
        "converted": converted,
        "conversion_rate": f"{(converted/total*100):.1f}%" if total > 0 else "0%"
    }