"""Team Inbox API — staff read & reply to WhatsApp/web conversations.

The piece that lets a clinic use ONE WhatsApp number for both the bot and a
human receptionist: the bot auto-replies, but staff can "take over" any chat
from the dashboard and reply by hand (sent from the clinic's own number).
While a chat is human-handled, the webhook stores incoming messages but the
bot stays silent (see routers/whatsapp.py::_handle_text).

Endpoints (clinic-scoped — every query filters by the caller's tenant):
    GET  /conversations                      list (unread first)
    GET  /conversations/{token}              full message thread (marks read)
    POST /conversations/{token}/reply        staff manual reply (WhatsApp send)
    POST /conversations/{token}/takeover     pause the bot for this chat
    POST /conversations/{token}/handback     resume the bot
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.chat import ChatSession
from app.models.user import User
from app.models.whatsapp_number import WhatsAppNumberMapping
from app.services.auth import get_current_user

router = APIRouter(prefix="/conversations", tags=["Team Inbox"])


def _channel(token: str) -> str:
    return "whatsapp" if (token or "").startswith("wa:") else "web"


def _wa_to(token: str) -> str:
    return token.split("wa:", 1)[1] if (token or "").startswith("wa:") else ""


def _last_message(session: ChatSession) -> dict:
    msgs = session.messages or []
    if not msgs:
        return {"role": "", "content": "", "preview": ""}
    last = msgs[-1]
    content = (last.get("content") or "").strip()
    return {"role": last.get("role", ""), "content": content, "preview": content[:80]}


def _scoped(db: Session, user: User):
    q = db.query(ChatSession).filter(ChatSession.tenant_id == user.tenant_id)
    # Branch-scoped staff only see their branch's conversations.
    if user.branch_id is not None:
        q = q.filter(
            or_(ChatSession.branch_id == user.branch_id, ChatSession.branch_id.is_(None))
        )
    return q


@router.get("")
def list_conversations(
    channel: Optional[str] = None,        # "whatsapp" | "web"
    mode: Optional[str] = None,           # "bot" | "human"
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Conversation list for the inbox — unread first, then most recent."""
    sessions = _scoped(db, current_user).order_by(
        ChatSession.updated_at.desc().nullslast(),
        ChatSession.created_at.desc(),
    ).limit(200).all()

    items = []
    for s in sessions:
        ch = _channel(s.session_token)
        if channel and ch != channel:
            continue
        if mode == "human" and not s.human_handling:
            continue
        if mode == "bot" and s.human_handling:
            continue
        last = _last_message(s)
        items.append({
            "session_token": s.session_token,
            "channel": ch,
            "patient_name": s.patient_name or _wa_to(s.session_token) or "Unknown",
            "patient_phone": s.patient_phone,
            "last_message": last["preview"],
            "last_role": last["role"],
            "unread": s.unread_count or 0,
            "human_handling": s.human_handling,
            "language": s.language,
            "updated_at": str(s.updated_at or s.created_at),
        })
    # Unread first, then recency (already ordered by recency from the query).
    items.sort(key=lambda x: (x["unread"] == 0,))
    return items


@router.get("/{session_token}")
def get_conversation(
    session_token: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Full thread. Opening a conversation clears its unread badge."""
    s = _scoped(db, current_user).filter(
        ChatSession.session_token == session_token
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if s.unread_count:
        s.unread_count = 0
        db.commit()
    return {
        "session_token": s.session_token,
        "channel": _channel(s.session_token),
        "patient_name": s.patient_name,
        "patient_phone": s.patient_phone,
        "alternate_phone": s.alternate_phone,
        "human_handling": s.human_handling,
        "language": s.language,
        "messages": s.messages or [],
    }


class ReplyIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


@router.post("/{session_token}/reply")
def send_reply(
    session_token: str,
    data: ReplyIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Staff manual reply. Sends over WhatsApp from the clinic's own number and
    appends to the thread. (Web-widget chats have no outbound push channel.)"""
    s = _scoped(db, current_user).filter(
        ChatSession.session_token == session_token
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if _channel(s.session_token) != "whatsapp":
        raise HTTPException(
            status_code=400,
            detail="This is a web-widget chat — it has no WhatsApp channel to reply on.",
        )

    # Send FROM this clinic's registered WhatsApp number.
    mapping = db.query(WhatsAppNumberMapping).filter(
        WhatsAppNumberMapping.tenant_id == current_user.tenant_id,
        WhatsAppNumberMapping.is_active.is_(True),
    ).first()
    from_pnid = mapping.phone_number_id if mapping else None

    from app.routers.whatsapp import _send_whatsapp_reply
    to = _wa_to(s.session_token)
    _send_whatsapp_reply(to, data.message, from_pnid=from_pnid)

    msgs = list(s.messages or [])
    # Tagged so the UI can show it came from a human agent, not the bot.
    msgs.append({"role": "assistant", "content": data.message, "by": "agent",
                 "agent": current_user.full_name or current_user.email})
    s.messages = msgs
    db.commit()
    return {"status": "sent", "sent_via": from_pnid or "global"}


@router.post("/{session_token}/takeover")
def takeover(
    session_token: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Pause the bot for this conversation so a human can handle it."""
    s = _scoped(db, current_user).filter(
        ChatSession.session_token == session_token
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Conversation not found")
    s.human_handling = True
    db.commit()
    return {"human_handling": True}


@router.post("/{session_token}/handback")
def handback(
    session_token: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Hand the conversation back to the bot."""
    s = _scoped(db, current_user).filter(
        ChatSession.session_token == session_token
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Conversation not found")
    s.human_handling = False
    db.commit()
    return {"human_handling": False}


@router.get("/meta/unread-count")
def unread_total(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Total unread across the clinic's conversations — for a sidebar badge."""
    from sqlalchemy import func
    total = _scoped(db, current_user).with_entities(
        func.coalesce(func.sum(ChatSession.unread_count), 0)
    ).scalar()
    return {"unread": int(total or 0)}
