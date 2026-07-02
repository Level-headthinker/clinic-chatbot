from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.note import Note
from app.models.user import User
from app.services.auth import get_current_user
from app.services.messaging import send_sms, send_whatsapp, send_email

router = APIRouter(prefix="/notes", tags=["Notes"])

NOTE_TYPES = ("note", "call", "sms", "email", "whatsapp")


class NoteCreate(BaseModel):
    content: str
    type: str = "note"
    patient_id: Optional[str] = None
    lead_id: Optional[str] = None
    # For outbound messages — phone or email to send to
    channel_target: Optional[str] = None


class NoteResponse(BaseModel):
    id: str
    type: str
    content: str
    patient_id: Optional[str]
    lead_id: Optional[str]
    channel_target: Optional[str]
    delivery_status: Optional[str]
    created_by: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


def _fmt(n: Note) -> NoteResponse:
    return NoteResponse(
        id=str(n.id),
        type=n.type,
        content=n.content,
        patient_id=str(n.patient_id) if n.patient_id else None,
        lead_id=str(n.lead_id) if n.lead_id else None,
        channel_target=n.channel_target,
        delivery_status=n.delivery_status,
        created_by=str(n.created_by) if n.created_by else None,
        created_at=n.created_at,
    )


def _base_query(current_user: User, db: Session):
    q = db.query(Note).filter(Note.tenant_id == current_user.tenant_id)
    if current_user.branch_id:
        q = q.filter(Note.branch_id == current_user.branch_id)
    return q


@router.get("", response_model=List[NoteResponse])
def list_notes(
    patient_id: Optional[str] = None,
    lead_id: Optional[str] = None,
    type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = _base_query(current_user, db)
    if patient_id:
        q = q.filter(Note.patient_id == patient_id)
    if lead_id:
        q = q.filter(Note.lead_id == lead_id)
    if type:
        q = q.filter(Note.type == type)
    return [_fmt(n) for n in q.order_by(Note.created_at.desc()).all()]


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    data: NoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if data.type not in NOTE_TYPES:
        raise HTTPException(status_code=400, detail=f"type must be one of {NOTE_TYPES}")

    delivery_status = None

    # Attempt outbound delivery for message types
    if data.type in ("sms", "whatsapp", "email") and data.channel_target:
        try:
            if data.type == "sms":
                send_sms(to=data.channel_target, body=data.content)
            elif data.type == "whatsapp":
                # Send FROM this clinic's own WhatsApp number, not the global one.
                from app.services.messaging import tenant_sender_pnid
                send_whatsapp(to=data.channel_target, body=data.content,
                              from_pnid=tenant_sender_pnid(db, current_user.tenant_id))
            elif data.type == "email":
                send_email(to=data.channel_target, subject="Message from your clinic", body=data.content)
            delivery_status = "sent"
        except Exception as exc:
            delivery_status = f"failed: {str(exc)[:120]}"

    note = Note(
        tenant_id=current_user.tenant_id,
        branch_id=current_user.branch_id,
        patient_id=data.patient_id or None,
        lead_id=data.lead_id or None,
        created_by=current_user.id,
        type=data.type,
        content=data.content,
        channel_target=data.channel_target,
        delivery_status=delivery_status,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return _fmt(note)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    note = _base_query(current_user, db).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    db.delete(note)
    db.commit()
