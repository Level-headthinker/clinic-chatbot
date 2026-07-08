"""WhatsApp AI Bot via Meta Cloud API webhook.

Flow
────
Patient sends WhatsApp message (text OR voice note) to the clinic number
  → Meta calls POST /whatsapp/webhook
  → we 200 immediately and process in the background (so Meta never retries)
  → load clinic context from DB (branch by phone_number_id)
  → voice notes: download media → VIS speech-to-text
  → run the SHARED brain (handle_turn) — answers AND books appointments
  → reply: text, or (for voice notes in WHATSAPP_VOICE_LANGS) a spoken voice note
    synthesized by VIS

Speech-to-text and text-to-speech are delegated to the VIS service
(VIS_API_URL / VIS_API_KEY). The clinic stays the brain; VIS is the voice I/O.

Setup (one-time)
────────────────
1. Meta for Developers → your App → WhatsApp → Configuration
2. Webhook URL: https://your-domain.com/whatsapp/webhook
3. Verify Token = META_VERIFY_TOKEN
4. Subscribe to the "messages" webhook field
5. Add META_PHONE_NUMBER_ID, META_ACCESS_TOKEN, META_VERIFY_TOKEN to .env
6. For voice notes, set VIS_API_URL (+ VIS_API_KEY) to your running VIS service.
"""
import hashlib
import hmac
import logging
import time
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.database import SessionLocal, get_db
from app.models.branch import Branch
from app.models.doctor import Doctor
from app.models.tenant import Tenant
from app.models.user import User
from app.models.whatsapp_number import WhatsAppNumberMapping
from app.services.auth import get_current_user
from app.services.conversation import handle_turn
from app.services.input_guard import run_input_guard

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp Bot"])
META_API_BASE = "https://graph.facebook.com/v19.0"

# Message-id de-dup — Meta redelivers if a 200 is slow; without this a retry
# would re-run the brain and double-reply (or double-book). Backed by Redis when
# configured so it works across multiple workers/replicas.
_SEEN_TTL = 600  # seconds


def _already_seen(message_id: str) -> bool:
    if not message_id:
        return False
    from app.services.rate_limit import dedup_seen
    return dedup_seen(f"wa:msg:{message_id}", _SEEN_TTL)


def _normalize_wa_phone(wa_id: str) -> str:
    """Meta sends numbers without + e.g. 923001234567. Normalize to 03XXXXXXXXX."""
    if wa_id.startswith("92") and len(wa_id) == 12:
        return "0" + wa_id[2:]
    return wa_id


def _verify_meta_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """Verify Meta's X-Hub-Signature-256 (HMAC-SHA256 of the raw body with the
    App Secret). Without this, anyone who finds the webhook URL can inject fake
    messages, burn the LLM quota, and make the clinic number send spam."""
    if not settings.META_APP_SECRET:
        if settings.ENVIRONMENT == "production":
            # FAIL CLOSED in production: without the App Secret we cannot prove a
            # webhook came from Meta — reject rather than accept forgeable input.
            logger.error("META_APP_SECRET unset in production — rejecting webhook")
            return False
        # Dev/staging convenience: allow, but log loudly on every request.
        logger.warning("META_APP_SECRET unset — skipping WhatsApp signature check (dev only)")
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(
        settings.META_APP_SECRET.encode(), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header.split("=", 1)[1])


def _load_context_for_phone(phone_number_id: str):
    """Resolve the clinic that owns this WhatsApp number. FAILS CLOSED:
    an unregistered phone_number_id gets no reply — never another clinic's data."""
    db = SessionLocal()
    try:
        branch = None
        mapping = db.query(WhatsAppNumberMapping).filter(
            WhatsAppNumberMapping.phone_number_id == phone_number_id,
            WhatsAppNumberMapping.is_active.is_(True),
        ).first()
        if mapping:
            if mapping.branch_id:
                branch = db.query(Branch).filter(
                    Branch.id == mapping.branch_id, Branch.is_active.is_(True)
                ).first()
            if not branch:  # mapping without branch → tenant's main branch
                branch = db.query(Branch).filter(
                    Branch.tenant_id == mapping.tenant_id,
                    Branch.is_active.is_(True),
                ).order_by(Branch.is_main_branch.desc()).first()
        # NOTE: the old fallback (Branch.phone == phone_number_id) is gone on
        # purpose. branch.phone is CLINIC-EDITABLE, so any clinic could set it to
        # a not-yet-mapped number's ID and capture that number's patient messages.
        # Routing now requires an explicit whatsapp_number_mappings row.
        if not branch:
            logger.warning("No clinic registered for phone_number_id=%s — ignoring", phone_number_id)
            return None, None, []
        tenant = db.query(Tenant).filter(
            Tenant.id == branch.tenant_id, Tenant.is_active.is_(True)
        ).first()
        if not tenant:
            return None, None, []
        doctors = db.query(Doctor).filter(
            Doctor.tenant_id == branch.tenant_id,
            Doctor.is_active.is_(True),
        ).all()
        return branch, tenant, list(doctors)
    finally:
        db.close()


def _check_message_quota(phone_number_id: str) -> tuple[bool, bool]:
    """Count one inbound message against the clinic's monthly limit.

    Returns ``(allowed, just_hit_limit)``. Numbers without a mapping row
    (legacy setups) are not limited. Counter auto-resets when a new month starts.
    """
    db = SessionLocal()
    try:
        mapping = db.query(WhatsAppNumberMapping).filter(
            WhatsAppNumberMapping.phone_number_id == phone_number_id,
        ).with_for_update().first()
        if not mapping:
            return True, False
        if not mapping.is_active:
            return False, False
        now = datetime.now(timezone.utc)
        if mapping.limit_reset_date is None or now >= mapping.limit_reset_date:
            mapping.messages_used_this_month = 0
            next_month = (now.replace(day=1) + timedelta(days=32)).replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
            mapping.limit_reset_date = next_month
        if mapping.messages_used_this_month >= mapping.message_limit_monthly:
            db.commit()
            return False, False
        mapping.messages_used_this_month += 1
        just_hit = mapping.messages_used_this_month >= mapping.message_limit_monthly
        db.commit()
        return True, just_hit
    except Exception:
        db.rollback()
        logger.exception("message quota check failed — allowing message")
        return True, False
    finally:
        db.close()


def _get_or_create_session(wa_from: str, branch, tenant, db):
    from app.models.chat import ChatSession
    session = db.query(ChatSession).filter(
        ChatSession.session_token == f"wa:{wa_from}",
        ChatSession.tenant_id == tenant.id,
    ).first()
    if not session:
        session = ChatSession(
            tenant_id=tenant.id,
            branch_id=branch.id,
            session_token=f"wa:{wa_from}",
            messages=[],
        )
        db.add(session)
        db.flush()
    return session


# ── Webhook verification (GET) ─────────────────────────────────────────────────

@router.get("/webhook")
async def verify_webhook(request: Request):
    """Meta calls this to verify the webhook URL."""
    params = request.query_params
    if params.get("hub.mode") == "subscribe" and \
            params.get("hub.verify_token") == settings.META_VERIFY_TOKEN:
        return PlainTextResponse(params.get("hub.challenge"))
    return PlainTextResponse("Forbidden", status_code=403)


# ── Webhook event handler (POST) ──────────────────────────────────────────────

@router.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    """Meta sends incoming WhatsApp messages here. We 200 fast and process async."""
    import json
    raw = await request.body()
    if not _verify_meta_signature(raw, request.headers.get("X-Hub-Signature-256")):
        logger.warning("WhatsApp webhook rejected: bad or missing signature")
        return PlainTextResponse("Forbidden", status_code=403)
    try:
        body = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return PlainTextResponse("Bad Request", status_code=400)

    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            phone_number_id = value.get("metadata", {}).get("phone_number_id", "")
            for msg in value.get("messages", []):
                if msg.get("type") not in ("text", "audio"):
                    continue  # ignore images, stickers, etc.
                if _already_seen(msg.get("id", "")):
                    continue
                background_tasks.add_task(_process_message, msg, phone_number_id)
            # Delivery statuses: Meta returns 200 on send even when delivery
            # later fails (e.g. free-form outside the 24h window). A "failed"
            # status flips the matching auto-reminder back to pending so staff
            # see the truth instead of a false "Sent".
            for st in value.get("statuses", []):
                if st.get("status") == "failed":
                    background_tasks.add_task(_process_failed_status, st)

    return {"status": "ok"}


def _process_failed_status(status: dict):
    """Mark the follow-up whose reminder message failed as NOT sent."""
    msg_id = status.get("id", "")
    if not msg_id:
        return
    from app.models.follow_up import FollowUp
    db = SessionLocal()
    try:
        fu = db.query(FollowUp).filter(FollowUp.wa_message_id == msg_id).first()
        if fu and fu.reminder_sent_at is not None:
            fu.reminder_sent_at = None
            fu.channel = None
            fu.status = "pending"   # back on the staff to-do list
            db.commit()
            logger.warning("Reminder %s failed to deliver — follow-up reopened", msg_id)
    except Exception:
        db.rollback()
    finally:
        db.close()


# ── Live-call turn endpoint (for the WhatsApp Calling voice agent) ──────────────
# The real-time call agent (self-hosted Pipecat) owns the audio/WebRTC; for each
# completed patient utterance it POSTs the transcript here and gets back the
# reply text to speak. This keeps ONE brain (handle_turn) for web chat, WhatsApp
# text, voice notes, and live calls — booking happens here, in the clinic DB.
# The call agent shares the WhatsApp session (token "wa:<number>") so a patient's
# text history and call carry the same memory.

class CallTurnRequest(BaseModel):
    phone_number_id: str = Field(..., max_length=64)
    caller: str = Field(..., max_length=32)        # WA number, e.g. 923001234567
    text: str = Field(..., min_length=1, max_length=1000)
    call_id: str | None = None                     # Meta call id, for logging only


class CallTurnResponse(BaseModel):
    reply: str
    language: str = "en"
    intent: str = ""


@router.post("/call/turn", response_model=CallTurnResponse)
def call_turn(data: CallTurnRequest, x_api_key: str | None = Header(default=None)):
    """One conversational turn of a live WhatsApp call. Reuses the shared brain."""
    # Shared-secret gate (same key the clinic uses to reach VIS). CLOSED by
    # default: a blank VIS_API_KEY disables the endpoint rather than opening it —
    # otherwise anyone could converse and book appointments as any caller.
    if not settings.VIS_API_KEY:
        raise HTTPException(status_code=503, detail="call agent not configured")
    if not x_api_key or not hmac.compare_digest(x_api_key, settings.VIS_API_KEY):
        raise HTTPException(status_code=401, detail="invalid api key")

    branch, tenant, _doctors = _load_context_for_phone(data.phone_number_id)
    if not branch or not tenant:
        return CallTurnResponse(
            reply="Sorry, we could not find your clinic.", language="en"
        )

    text = data.text.strip()[:1000]
    if not text:
        return CallTurnResponse(reply="", language="en")

    reply = "Sorry, something went wrong. Please try again."
    language = "en"
    intent = ""
    db = SessionLocal()
    try:
        session = _get_or_create_session(data.caller, branch, tenant, db)
        guard = run_input_guard(text, f"wa:{data.caller}")
        if not guard.allowed:
            db.rollback()
            return CallTurnResponse(
                reply=guard.blocked_reason or "I cannot process that.",
                language="en", intent="blocked",
            )
        if not session.patient_phone:
            session.patient_phone = _normalize_wa_phone(data.caller)
        reply, intent, language = handle_turn(
            db, branch, tenant, session, guard.sanitized_message, modality="voice"
        )
    except Exception as e:  # noqa: BLE001 — never 500 a live call; speak a fallback
        db.rollback()
        print(f"⚠️  call turn error: {e}")
    finally:
        db.close()

    return CallTurnResponse(reply=reply, language=language, intent=intent)


def _process_message(msg: dict, phone_number_id: str):
    """Route one inbound message. Runs in the background; never raises."""
    from app.observability import report_error
    mtype = msg.get("type")
    wa_from = msg.get("from", "")
    try:
        allowed, just_hit = _check_message_quota(phone_number_id)
        if not allowed:
            logger.warning("Monthly message limit reached for %s — dropping", phone_number_id)
            return
        if just_hit:
            _send_whatsapp_reply(
                wa_from,
                "Our automated assistant has reached its monthly message limit. "
                "Please call the clinic directly — we're happy to help.",
                from_pnid=phone_number_id,
            )
        if mtype == "text":
            text = (msg.get("text", {}).get("body") or "").strip()
            if text:
                _handle_text(wa_from, text[:1000], phone_number_id)
        elif mtype == "audio":
            _handle_voice(wa_from, msg["audio"]["id"], phone_number_id)
    except Exception as e:  # noqa: BLE001 — background task must not crash the worker
        # A background task that fails here means a patient message got no reply
        # and Meta already 200'd — surface it instead of losing it silently.
        report_error("WhatsApp inbound processing failed", e,
                     type=mtype, phone_number_id=phone_number_id)


def _store_inbound(session, text: str):
    """Append a patient message to the conversation and bump the unread badge —
    used when a human has taken the chat over (bot stays silent)."""
    msgs = list(session.messages or [])
    msgs.append({"role": "user", "content": text})
    session.messages = msgs
    session.unread_count = (session.unread_count or 0) + 1


def _handle_text(wa_from: str, text: str, phone_number_id: str):
    branch, tenant, _doctors = _load_context_for_phone(phone_number_id)
    if not branch or not tenant:
        print(f"⚠️  No clinic found for phone_number_id={phone_number_id}")
        _send_whatsapp_reply(wa_from, "Sorry, we could not find your clinic. Please contact us directly.", from_pnid=phone_number_id)
        return

    reply = "Sorry, something went wrong. Please try again or call the clinic directly."
    db = SessionLocal()
    try:
        session = _get_or_create_session(wa_from, branch, tenant, db)
        if not session.patient_phone:
            session.patient_phone = _normalize_wa_phone(wa_from)
        # Human takeover: a staff member is handling this chat — store the
        # patient's message for the inbox and stay quiet (no bot reply).
        if session.human_handling:
            _store_inbound(session, text)
            db.commit()
            return
        guard = run_input_guard(text, f"wa:{wa_from}")
        if not guard.allowed:
            db.rollback()
            _send_whatsapp_reply(wa_from, guard.blocked_reason or "I cannot process that message.", from_pnid=phone_number_id)
            return
        reply, _intent, _lang = handle_turn(
            db, branch, tenant, session, guard.sanitized_message, modality="text"
        )
        session.unread_count = (session.unread_count or 0) + 1  # patient turn unseen by staff
        db.commit()
    except Exception as e:  # noqa: BLE001
        db.rollback()
        print(f"⚠️  WhatsApp text handler error: {e}")
    finally:
        db.close()

    _send_whatsapp_reply(wa_from, reply, from_pnid=phone_number_id)


def _handle_voice(wa_from: str, media_id: str, phone_number_id: str):
    branch, tenant, _doctors = _load_context_for_phone(phone_number_id)
    if not branch or not tenant:
        _send_whatsapp_reply(wa_from, "Sorry, we could not find your clinic. Please contact us directly.", from_pnid=phone_number_id)
        return

    audio, mime = _download_media(media_id)
    if not audio:
        _send_whatsapp_reply(wa_from, "Sorry, I couldn't read that voice note. Please try again.", from_pnid=phone_number_id)
        return

    transcript, _stt_lang = _transcribe_via_vis(audio, mime)
    if not transcript:
        _send_whatsapp_reply(wa_from, "I couldn't hear anything in that message. Could you resend it?", from_pnid=phone_number_id)
        return

    reply = "Sorry, something went wrong. Please try again or call the clinic directly."
    reply_language = "en"
    db = SessionLocal()
    try:
        session = _get_or_create_session(wa_from, branch, tenant, db)
        if not session.patient_phone:
            session.patient_phone = _normalize_wa_phone(wa_from)
        # Human takeover: store the transcribed voice note for the inbox, no bot.
        if session.human_handling:
            _store_inbound(session, f"🎤 {transcript}")
            db.commit()
            return
        guard = run_input_guard(transcript, f"wa:{wa_from}")
        if not guard.allowed:
            db.rollback()
            _send_whatsapp_reply(wa_from, guard.blocked_reason or "I cannot process that message.", from_pnid=phone_number_id)
            return
        reply, _intent, reply_language = handle_turn(
            db, branch, tenant, session, guard.sanitized_message, modality="voice"
        )
        session.unread_count = (session.unread_count or 0) + 1
        db.commit()
    except Exception as e:  # noqa: BLE001
        db.rollback()
        print(f"⚠️  WhatsApp voice handler error: {e}")
    finally:
        db.close()

    # Reply as a voice note for configured languages; otherwise text.
    if reply_language in settings.whatsapp_voice_langs and _reply_with_voice(wa_from, reply, reply_language, from_pnid=phone_number_id):
        return
    _send_whatsapp_reply(wa_from, reply, from_pnid=phone_number_id)


def _reply_with_voice(wa_from: str, text: str, language: str, from_pnid: str | None = None) -> bool:
    """Synthesize via VIS and send as a WhatsApp voice note. Returns False on any failure."""
    if not text:
        return False
    try:
        audio, mime = _synthesize_via_vis(text, language)
        if audio:
            media_id = _upload_media(audio, mime, from_pnid=from_pnid)
            if media_id:
                _send_whatsapp_audio(wa_from, media_id, from_pnid=from_pnid)
                return True
    except Exception as e:  # noqa: BLE001
        print(f"⚠️  voice reply failed: {e}")
    return False


# ── VIS (voice service) calls ──────────────────────────────────────────────────

def _vis_headers() -> dict:
    return {"X-API-Key": settings.VIS_API_KEY} if settings.VIS_API_KEY else {}


def _transcribe_via_vis(audio: bytes, mime: str) -> tuple[str, str]:
    if not settings.VIS_API_URL:
        print("⚠️  VIS_API_URL not set — cannot transcribe voice note")
        return "", "en"
    try:
        resp = httpx.post(
            f"{settings.VIS_API_URL.rstrip('/')}/voice/transcribe",
            headers=_vis_headers(),
            files={"file": ("note.ogg", audio, mime or "audio/ogg")},
            timeout=60,
        )
        if resp.status_code != 200:
            print(f"⚠️  VIS transcribe failed: {resp.status_code} — {resp.text}")
            return "", "en"
        data = resp.json()
        return (data.get("transcript") or "").strip(), data.get("language") or "en"
    except Exception as e:  # noqa: BLE001
        print(f"⚠️  VIS transcribe error: {e}")
        return "", "en"


def _synthesize_via_vis(text: str, language: str) -> tuple[bytes, str]:
    if not settings.VIS_API_URL:
        return b"", ""
    try:
        resp = httpx.post(
            f"{settings.VIS_API_URL.rstrip('/')}/voice/synthesize",
            headers=_vis_headers(),
            data={"text": text, "language": language, "audio_format": "ogg_opus"},
            timeout=60,
        )
        if resp.status_code != 200:
            print(f"⚠️  VIS synthesize failed: {resp.status_code} — {resp.text}")
            return b"", ""
        return resp.content, resp.headers.get("content-type", "audio/ogg")
    except Exception as e:  # noqa: BLE001
        print(f"⚠️  VIS synthesize error: {e}")
        return b"", ""


# ── Meta media + send helpers ──────────────────────────────────────────────────

def _meta_auth() -> dict:
    return {"Authorization": f"Bearer {settings.META_ACCESS_TOKEN}"}


def _download_media(media_id: str) -> tuple[bytes, str]:
    try:
        meta = httpx.get(f"{META_API_BASE}/{media_id}", headers=_meta_auth(), timeout=30)
        if meta.status_code != 200:
            print(f"⚠️  media lookup failed: {meta.status_code} — {meta.text}")
            return b"", ""
        info = meta.json()
        url, mime = info.get("url"), info.get("mime_type", "audio/ogg")
        media = httpx.get(url, headers=_meta_auth(), timeout=30)
        if media.status_code != 200:
            print(f"⚠️  media download failed: {media.status_code}")
            return b"", ""
        return media.content, mime
    except Exception as e:  # noqa: BLE001
        print(f"⚠️  media download error: {e}")
        return b"", ""


def _upload_media(data: bytes, mime: str, from_pnid: str | None = None) -> str:
    ext = "ogg" if "ogg" in (mime or "") else "mp3"
    sender = from_pnid or settings.META_PHONE_NUMBER_ID
    try:
        resp = httpx.post(
            f"{META_API_BASE}/{sender}/media",
            headers=_meta_auth(),
            data={"messaging_product": "whatsapp", "type": mime},
            files={"file": (f"reply.{ext}", data, mime)},
            timeout=30,
        )
        if resp.status_code != 200:
            print(f"⚠️  media upload failed: {resp.status_code} — {resp.text}")
            return ""
        return resp.json().get("id", "")
    except Exception as e:  # noqa: BLE001
        print(f"⚠️  media upload error: {e}")
        return ""


def _send_whatsapp_audio(to: str, media_id: str, from_pnid: str | None = None):
    sender = from_pnid or settings.META_PHONE_NUMBER_ID
    if not sender or not settings.META_ACCESS_TOKEN:
        return
    try:
        resp = httpx.post(
            f"{META_API_BASE}/{sender}/messages",
            headers=_meta_auth(),
            json={"messaging_product": "whatsapp", "to": to, "type": "audio", "audio": {"id": media_id}},
            timeout=10,
        )
        if resp.status_code != 200:
            print(f"⚠️  WhatsApp audio send failed: {resp.status_code} — {resp.text}")
    except Exception as e:  # noqa: BLE001
        print(f"⚠️  WhatsApp audio send exception: {e}")


# ── Clinic dashboard: own number's monthly usage ───────────────────────────────

@router.get("/usage")
def whatsapp_usage(
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """The logged-in clinic's WhatsApp numbers with monthly usage vs limit."""
    mappings = db.query(WhatsAppNumberMapping).filter(
        WhatsAppNumberMapping.tenant_id == current_user.tenant_id
    ).all()
    return [
        {
            "id": str(m.id),
            "whatsapp_number": m.whatsapp_number,
            "is_active": m.is_active,
            "limit": m.message_limit_monthly,
            "used": m.messages_used_this_month,
            "remaining": max(0, m.message_limit_monthly - m.messages_used_this_month),
            "resets_at": str(m.limit_reset_date) if m.limit_reset_date else None,
        }
        for m in mappings
    ]


def _send_whatsapp_reply(to: str, body: str, from_pnid: str | None = None):
    if not body:
        return
    # Reply FROM the number that received the message — WhatsApp's 24h service
    # window is per-number, so sending from any other number would fail to
    # deliver in-session. Falls back to the global number for legacy single-number.
    from app.observability import report_error
    sender = from_pnid or settings.META_PHONE_NUMBER_ID
    if not sender or not settings.META_ACCESS_TOKEN:
        report_error("WhatsApp reply skipped: META credentials not set")
        return
    try:
        resp = httpx.post(
            f"{META_API_BASE}/{sender}/messages",
            headers=_meta_auth(),
            json={"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": body}},
            timeout=10,
        )
        if resp.status_code != 200:
            # A non-200 here (esp. 401/190 = expired token) means the bot has
            # effectively gone dark for this clinic — must not be silent.
            report_error("WhatsApp reply failed", status=resp.status_code,
                         detail=resp.text[:200], sender=sender)
    except Exception as e:  # noqa: BLE001
        report_error("WhatsApp reply exception", e, sender=sender)
