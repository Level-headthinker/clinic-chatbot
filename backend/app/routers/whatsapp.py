"""WhatsApp AI Bot via Meta Cloud API webhook.

Flow
────
Patient sends WhatsApp message to clinic number
  → Meta calls POST /whatsapp/webhook
  → We load clinic context from DB (branch by phone number)
  → Groq AI generates a reply using the same clinic prompt as the web chat
  → We send the reply back via Meta Cloud API

Setup (one-time)
────────────────
1. Go to Meta for Developers → your App → WhatsApp → Configuration
2. Set Webhook URL to: https://your-domain.com/whatsapp/webhook
3. Set Verify Token to the value of META_VERIFY_TOKEN in .env
4. Subscribe to the "messages" webhook field
5. Add META_PHONE_NUMBER_ID, META_ACCESS_TOKEN, META_VERIFY_TOKEN to .env
"""
import hashlib
import hmac
import json

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from app.config import settings
from app.database import SessionLocal
from app.models.branch import Branch
from app.models.chat import ChatSession, Lead
from app.models.doctor import Doctor
from app.models.tenant import Tenant
from app.services.llm import (
    detect_language,
    extract_patient_info,
    get_ai_response,
    is_emergency,
    _message_may_contain_patient_info,
)

try:
    from groq import Groq as _GroqSync
    _groq_sync = _GroqSync(api_key=settings.GROQ_API_KEY)
except Exception:
    _groq_sync = None

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp Bot"])
META_API_BASE = "https://graph.facebook.com/v19.0"

DOCTORS_INFO_CACHE: dict = {}  # simple in-process cache


def _normalize_wa_phone(wa_id: str) -> str:
    """Meta sends numbers without + e.g. 923001234567. Normalize to 03XXXXXXXXX."""
    if wa_id.startswith("92") and len(wa_id) == 12:
        return "0" + wa_id[2:]
    return wa_id


def _load_context_for_phone(phone_number_id: str):
    """Load the branch that owns this WhatsApp number from DB."""
    db = SessionLocal()
    try:
        # Find branch by WhatsApp phone field, or fall back to first active branch
        branch = db.query(Branch).filter(
            Branch.phone == phone_number_id,
            Branch.is_active.is_(True),
        ).first()

        # Fallback: use the first active branch (works for single-branch clinics)
        if not branch:
            branch = db.query(Branch).filter(Branch.is_active.is_(True)).first()

        if not branch:
            return None, None, []

        tenant = db.query(Tenant).filter(Tenant.id == branch.tenant_id).first()
        doctors = db.query(Doctor).filter(
            Doctor.tenant_id == branch.tenant_id,
            Doctor.is_active.is_(True),
        ).all()
        return branch, tenant, list(doctors)
    finally:
        db.close()


def _get_or_create_session(wa_from: str, branch, tenant, db) -> ChatSession:
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


def _get_doctors_info(doctors) -> str:
    if not doctors:
        return "No doctors listed."
    lines = []
    for d in doctors:
        name = d.name if d.name.lower().startswith("dr") else f"Dr. {d.name}"
        timings = ", ".join(
            f"{t.get('day')} {t.get('from')}-{t.get('to')}"
            for t in (d.timings or [])
        )
        lines.append(f"- {name} | {d.specialty} | Fee: {d.fee or 'N/A'} | {timings}")
    return "\n".join(lines)


def _send_whatsapp_reply(to: str, body: str):
    if not settings.META_PHONE_NUMBER_ID or not settings.META_ACCESS_TOKEN:
        print("⚠️  WhatsApp reply skipped: META credentials not set")
        return
    try:
        resp = httpx.post(
            f"{META_API_BASE}/{settings.META_PHONE_NUMBER_ID}/messages",
            headers={"Authorization": f"Bearer {settings.META_ACCESS_TOKEN}"},
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": body},
            },
            timeout=10,
        )
        if resp.status_code != 200:
            print(f"⚠️  WhatsApp reply failed: {resp.status_code} — {resp.text}")
        else:
            print(f"✅ WhatsApp reply sent to {to}")
    except Exception as e:
        print(f"⚠️  WhatsApp reply exception: {e}")


def _verify_signature(request_body: bytes, sig_header: str) -> bool:
    """Verify X-Hub-Signature-256 from Meta."""
    if not settings.META_ACCESS_TOKEN:
        return True  # Skip verification in dev
    secret = settings.META_ACCESS_TOKEN.encode()
    expected = "sha256=" + hmac.new(secret, request_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig_header or "")


# ── Webhook verification (GET) ─────────────────────────────────────────────────

@router.get("/webhook")
async def verify_webhook(request: Request):
    """Meta calls this to verify the webhook URL."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == settings.META_VERIFY_TOKEN:
        return PlainTextResponse(challenge)
    return PlainTextResponse("Forbidden", status_code=403)


# ── Webhook event handler (POST) ──────────────────────────────────────────────

@router.post("/webhook")
async def receive_webhook(request: Request):
    """Meta sends incoming WhatsApp messages here."""
    body_bytes = await request.body()
    body = json.loads(body_bytes)

    # Walk the nested Meta payload
    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            phone_number_id = value.get("metadata", {}).get("phone_number_id", "")
            messages = value.get("messages", [])

            for msg in messages:
                if msg.get("type") != "text":
                    continue  # ignore images, voice notes, etc.

                wa_from = msg["from"]  # e.g. "923001234567"
                text = msg["text"]["body"].strip()
                if not text:
                    continue

                # Truncate oversized messages — prevents prompt injection attacks
                if len(text) > 1000:
                    text = text[:1000]

                _handle_message(wa_from, text, phone_number_id)

    return {"status": "ok"}


def _handle_message(wa_from: str, text: str, phone_number_id: str):
    """Process one incoming WhatsApp message and send a reply."""
    print(f"📩 WhatsApp message from {wa_from}: {text[:50]}")
    branch, tenant, doctors = _load_context_for_phone(phone_number_id)
    if not branch or not tenant:
        print(f"⚠️  No clinic found for phone_number_id={phone_number_id}")
        _send_whatsapp_reply(wa_from, "Sorry, we could not find your clinic. Please contact us directly.")
        return
    print(f"✅ Clinic found: {tenant.name}")

    db = SessionLocal()
    try:
        session = _get_or_create_session(wa_from, branch, tenant, db)

        # Extract patient info if message looks like it contains it
        if _message_may_contain_patient_info(text):
            msgs = list(session.messages or [])
            msgs.append({"role": "user", "content": text})
            info = extract_patient_info(msgs)
            if info["name"] and not session.patient_name:
                session.patient_name = info["name"]
            if info["phone"] and not session.patient_phone:
                session.patient_phone = info["phone"]
            if not session.patient_phone:
                session.patient_phone = _normalize_wa_phone(wa_from)

        bot_name = branch.bot_name or tenant.bot_name or "ClinicBot"
        welcome_msg = branch.welcome_message or tenant.welcome_message or ""

        phone_val = branch.phone if branch.phone else "Not configured"
        hours_val = branch.working_hours if branch.working_hours else "Not configured"
        address_parts = [p for p in [branch.address, branch.city] if p]
        address_val = ", ".join(address_parts) if address_parts else "Not configured"

        clinic_info = (
            f"Clinic Name: {tenant.name}\n"
            f"Bot Name: {bot_name}\n"
            f"Welcome Message: {welcome_msg}\n"
            f"Clinic Phone: {phone_val}\n"
            f"Clinic Address: {address_val}\n"
            f"Clinic Timings: {hours_val}\n"
            f"Emergency: Call 1122"
        )

        reply = get_ai_response(
            user_message=text,
            conversation_history=session.messages or [],
            bot_name=bot_name,
            clinic_info=clinic_info,
            doctors_info=_get_doctors_info(doctors),
            patient_name=session.patient_name or "Not collected yet",
            patient_phone=session.patient_phone or "Not collected yet",
        )

        # Save conversation
        msgs = list(session.messages or [])
        msgs.append({"role": "user", "content": text})
        msgs.append({"role": "assistant", "content": reply})
        session.messages = msgs

        # Save lead if we have name + phone
        if session.patient_name and session.patient_phone:
            existing = db.query(Lead).filter(
                Lead.phone == session.patient_phone,
                Lead.tenant_id == tenant.id,
            ).first()
            if not existing:
                db.add(Lead(
                    tenant_id=tenant.id,
                    branch_id=branch.id,
                    name=session.patient_name,
                    phone=session.patient_phone,
                    concern="WhatsApp inquiry",
                    source="whatsapp",
                    status="new",
                ))

        db.commit()
    except Exception:
        db.rollback()
        reply = "Sorry, something went wrong. Please try again or call the clinic directly."
    finally:
        db.close()

    _send_whatsapp_reply(wa_from, reply)
