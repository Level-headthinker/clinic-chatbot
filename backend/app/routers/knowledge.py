"""Clinic Knowledge Base API — the clinic teaches its bot answers to common
patient questions (pricing, pre-care, policies, parking, insurance, …). The bot
retrieves the relevant ones at answer time (see services/knowledge_retrieval.py).

Clinic-scoped: every query filters by the caller's tenant, so one clinic's
knowledge is never visible to another.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.knowledge import KnowledgeEntry
from app.models.user import User
from app.services.auth import require_admin_user
from app.services.knowledge_retrieval import retrieve_knowledge
from app.services import knowledge_ingest as ingest

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10MB


class KnowledgeIn(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    answer: str = Field(min_length=2, max_length=4000)
    category: Optional[str] = Field(default=None, max_length=100)
    is_active: bool = True


class UrlIn(BaseModel):
    url: str = Field(min_length=4, max_length=2000)
    category: Optional[str] = Field(default=None, max_length=100)


def _fmt(e: KnowledgeEntry) -> dict:
    return {
        "id": str(e.id),
        "question": e.question,
        "answer": e.answer,
        "category": e.category,
        "is_active": e.is_active,
        "created_at": str(e.created_at),
        "source_type": e.source_type or "manual",
        "source_name": e.source_name,
        "source_ref": str(e.source_ref) if e.source_ref else None,
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


@router.post("/ingest/document", status_code=201)
async def ingest_document(
    file: UploadFile = File(...),
    category: Optional[str] = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    """Upload a PDF / DOCX / TXT — its text is extracted, chunked, and stored so
    the bot can answer from it."""
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="The file is empty.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 10MB).")
    try:
        text = ingest.extract_text_from_file(file.filename, raw)
        result = ingest.ingest_text(
            db, tenant_id=current_user.tenant_id, branch_id=current_user.branch_id,
            source_type="document", source_name=file.filename or "document",
            text=text, category=(category or None),
        )
    except ingest.IngestError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@router.post("/ingest/url", status_code=201)
def ingest_url(
    data: UrlIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    """Read a public web page and store its text so the bot can answer from it."""
    try:
        title, text = ingest.extract_text_from_url(data.url.strip())
        result = ingest.ingest_text(
            db, tenant_id=current_user.tenant_id, branch_id=current_user.branch_id,
            source_type="web", source_name=title or data.url.strip(),
            text=text, category=(data.category or None),
        )
    except ingest.IngestError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@router.delete("/source/{source_ref}", status_code=200)
def delete_source(
    source_ref: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    """Remove every chunk that came from one uploaded document / web page."""
    deleted = db.query(KnowledgeEntry).filter(
        KnowledgeEntry.tenant_id == current_user.tenant_id,
        KnowledgeEntry.source_ref == source_ref,
    ).delete(synchronize_session=False)
    db.commit()
    if not deleted:
        raise HTTPException(status_code=404, detail="Source not found")
    return {"deleted": deleted}


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
