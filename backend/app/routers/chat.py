"""Web chat widget endpoint.

The conversational/booking logic now lives in ``app/services/conversation.py``
(``handle_turn``) so the web chat, WhatsApp, and voice all share one brain. This
router only does the channel-specific parts: rate limiting, the input guard, and
resolving the branch + session before delegating.
"""
from collections import defaultdict
import time
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.branch import Branch
from app.models.chat import ChatSession
from app.models.user import User
from app.services.auth import get_current_user
from app.services.conversation import handle_turn
from app.services.conversation_logger import log_input_flag
from app.services.input_guard import run_input_guard
from app.services.llm import detect_language

router = APIRouter(prefix="/chat", tags=["Chat"])


class MessageRequest(BaseModel):
    session_token: Optional[str] = None
    branch_slug: str = Field(max_length=100)
    message: str = Field(min_length=1, max_length=1000)


class MessageResponse(BaseModel):
    session_token: str
    reply: str
    intent: str
    language: str


# ── Chat rate limiter (per IP) ────────────────────────────────────────────────
_chat_attempts: dict[str, list[float]] = defaultdict(list)


def _chat_rate_limit(request: Request):
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    window = 60  # 1 minute
    max_msgs = 30  # max 30 messages per minute per IP
    cutoff = now - window
    attempts = [t for t in _chat_attempts[ip] if t > cutoff]
    _chat_attempts[ip] = attempts
    if len(attempts) >= max_msgs:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many messages. Please slow down."
        )
    _chat_attempts[ip].append(now)


# ════════════════════════════════════════════════════════════
# MAIN CHAT ENDPOINT
# ════════════════════════════════════════════════════════════

@router.post("/message", response_model=MessageResponse)
def send_message(data: MessageRequest, request: Request, db: Session = Depends(get_db)):
    _chat_rate_limit(request)

    # ── INPUT GUARD ──────────────────────────────────────────
    client_ip = request.client.host if request.client else "unknown"
    guard_key = data.session_token or f"pre-session:{data.branch_slug}:{client_ip}"
    guard = run_input_guard(data.message, guard_key)

    if not guard.allowed:
        lang = detect_language(data.message)
        if guard.should_log:
            log_input_flag(
                db=db,
                flag_type=guard.flag or "unknown",
                flagged_message=guard.sanitized_message,
                blocked_reason=guard.blocked_reason,
                session_token=data.session_token,
                tenant_id=None,
            )
        reply = (
            f"معذرت — {guard.blocked_reason}"
            if lang in ["ur", "ur-roman"]
            else guard.blocked_reason or "I cannot process that message."
        )
        return MessageResponse(
            session_token=data.session_token or "",
            reply=reply, intent="blocked", language=lang
        )

    clean_message = guard.sanitized_message

    # ── Resolve branch → tenant ──────────────────────────────
    branch = db.query(Branch).options(joinedload(Branch.tenant)).filter(
        Branch.slug == data.branch_slug, Branch.is_active == True
    ).first()
    if not branch or not branch.tenant or not branch.tenant.is_active:
        raise HTTPException(status_code=404, detail="Clinic not found")
    tenant = branch.tenant

    # ── Resolve or create session ────────────────────────────
    session = None
    if data.session_token:
        session = db.query(ChatSession).filter(
            ChatSession.session_token == data.session_token,
            ChatSession.tenant_id == tenant.id
        ).first()

    if not session:
        session = ChatSession(
            tenant_id=tenant.id,
            branch_id=branch.id,
            session_token=str(uuid.uuid4()),
            messages=[],
            language=detect_language(clean_message)
        )
        db.add(session)
        db.flush()

    # ── Delegate to the shared brain ─────────────────────────
    reply, intent, language = handle_turn(
        db, branch, tenant, session, clean_message, modality="text"
    )

    return MessageResponse(
        session_token=session.session_token,
        reply=reply, intent=intent, language=language
    )


@router.get("/session/{session_token}")
def get_session(
    session_token: str,
    branch_slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    branch = db.query(Branch).filter(
        Branch.slug == branch_slug, Branch.is_active == True
    ).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Clinic not found")
    tenant_id = branch.tenant_id
    if not current_user.is_superadmin and current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    session = db.query(ChatSession).filter(
        ChatSession.session_token == session_token,
        ChatSession.tenant_id == tenant_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_token": session.session_token,
        "messages": session.messages,
        "language": session.language,
        "patient_name": session.patient_name,
        "patient_phone": session.patient_phone,
    }
