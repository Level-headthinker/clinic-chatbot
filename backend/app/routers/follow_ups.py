from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.follow_up import FollowUp
from app.models.user import User
from app.services.auth import get_current_user

router = APIRouter(prefix="/follow-ups", tags=["Follow-ups"])


class FollowUpCreate(BaseModel):
    title: str
    notes: Optional[str] = None
    due_date: datetime
    patient_id: Optional[str] = None
    lead_id: Optional[str] = None
    assigned_to: Optional[str] = None


class FollowUpUpdate(BaseModel):
    title: Optional[str] = None
    notes: Optional[str] = None
    due_date: Optional[datetime] = None
    status: Optional[str] = None
    assigned_to: Optional[str] = None


class FollowUpResponse(BaseModel):
    id: str
    title: str
    notes: Optional[str]
    due_date: datetime
    status: str
    patient_id: Optional[str]
    lead_id: Optional[str]
    assigned_to: Optional[str]
    created_by: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


def _fmt(f: FollowUp) -> FollowUpResponse:
    return FollowUpResponse(
        id=str(f.id),
        title=f.title,
        notes=f.notes,
        due_date=f.due_date,
        status=f.status,
        patient_id=str(f.patient_id) if f.patient_id else None,
        lead_id=str(f.lead_id) if f.lead_id else None,
        assigned_to=str(f.assigned_to) if f.assigned_to else None,
        created_by=str(f.created_by) if f.created_by else None,
        created_at=f.created_at,
    )


def _base_query(current_user: User, db: Session):
    q = db.query(FollowUp).filter(FollowUp.tenant_id == current_user.tenant_id)
    if current_user.branch_id:
        q = q.filter(FollowUp.branch_id == current_user.branch_id)
    return q


@router.get("", response_model=List[FollowUpResponse])
def list_follow_ups(
    status: Optional[str] = None,
    patient_id: Optional[str] = None,
    lead_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = _base_query(current_user, db)
    if status:
        q = q.filter(FollowUp.status == status)
    if patient_id:
        q = q.filter(FollowUp.patient_id == patient_id)
    if lead_id:
        q = q.filter(FollowUp.lead_id == lead_id)
    return [_fmt(f) for f in q.order_by(FollowUp.due_date.asc()).all()]


@router.post("", response_model=FollowUpResponse, status_code=status.HTTP_201_CREATED)
def create_follow_up(
    data: FollowUpCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    fu = FollowUp(
        tenant_id=current_user.tenant_id,
        branch_id=current_user.branch_id,
        patient_id=data.patient_id or None,
        lead_id=data.lead_id or None,
        assigned_to=data.assigned_to or None,
        created_by=current_user.id,
        title=data.title,
        notes=data.notes,
        due_date=data.due_date,
    )
    db.add(fu)
    db.commit()
    db.refresh(fu)
    return _fmt(fu)


@router.put("/{fu_id}", response_model=FollowUpResponse)
def update_follow_up(
    fu_id: str,
    data: FollowUpUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    fu = _base_query(current_user, db).filter(FollowUp.id == fu_id).first()
    if not fu:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(fu, field, value)
    db.commit()
    db.refresh(fu)
    return _fmt(fu)


@router.patch("/{fu_id}/done", response_model=FollowUpResponse)
def mark_done(
    fu_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    fu = _base_query(current_user, db).filter(FollowUp.id == fu_id).first()
    if not fu:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    fu.status = "done"
    db.commit()
    db.refresh(fu)
    return _fmt(fu)


@router.delete("/{fu_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_follow_up(
    fu_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    fu = _base_query(current_user, db).filter(FollowUp.id == fu_id).first()
    if not fu:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    db.delete(fu)
    db.commit()
