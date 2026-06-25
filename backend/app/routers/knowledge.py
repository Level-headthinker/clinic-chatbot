"""Clinic Knowledge Base API — the clinic teaches its bot answers to common
patient questions (pricing, pre-care, policies, parking, insurance, …). The bot
retrieves the relevant ones at answer time (see services/knowledge_retrieval.py).

Clinic-scoped: every query filters by the caller's tenant, so one clinic's
knowledge is never visible to another.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.knowledge import KnowledgeEntry
from app.models.user import User
from app.services.auth import require_admin_user
from app.services.knowledge_retrieval import retrieve_knowledge

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])


class KnowledgeIn(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    answer: str = Field(min_length=2, max_length=4000)
    category: Optional[str] = Field(default=None, max_length=100)
    is_active: bool = True


def _fmt(e: KnowledgeEntry) -> dict:
    return {
        "id": str(e.id),
        "question": e.question,
        "answer": e.answer,
        "category": e.category,
        "is_active": e.is_active,
        "created_at": str(e.created_at),
    }


@router.get("")
def list_entries(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    entries = db.query(KnowledgeEntry).filter(
        KnowledgeEntry.tenant_id == current_user.tenant_id
    ).order_by(KnowledgeEntry.created_at.desc()).all()
    return [_fmt(e) for e in entries]


@router.post("", status_code=201)
def create_entry(
    data: KnowledgeIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    entry = KnowledgeEntry(
        tenant_id=current_user.tenant_id,
        branch_id=current_user.branch_id,
        question=data.question.strip(),
        answer=data.answer.strip(),
        category=(data.category or "").strip() or None,
        is_active=data.is_active,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _fmt(entry)


def _get_owned(entry_id: str, current_user: User, db: Session) -> KnowledgeEntry:
    entry = db.query(KnowledgeEntry).filter(
        KnowledgeEntry.id == entry_id,
        KnowledgeEntry.tenant_id == current_user.tenant_id,
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


@router.put("/{entry_id}")
def update_entry(
    entry_id: str,
    data: KnowledgeIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    entry = _get_owned(entry_id, current_user, db)
    entry.question = data.question.strip()
    entry.answer = data.answer.strip()
    entry.category = (data.category or "").strip() or None
    entry.is_active = data.is_active
    db.commit()
    db.refresh(entry)
    return _fmt(entry)


@router.delete("/{entry_id}", status_code=204)
def delete_entry(
    entry_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    entry = _get_owned(entry_id, current_user, db)
    db.delete(entry)
    db.commit()


@router.get("/test")
def test_retrieval(
    q: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    """Preview what the bot would retrieve for a sample patient question."""
    return {"query": q, "matches": retrieve_knowledge(db, current_user.tenant_id, q, k=3)}
