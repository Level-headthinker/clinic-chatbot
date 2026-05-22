"""AI Voice Agent via VAPI.ai (replaces Twilio Voice).

Architecture
────────────
Inbound call  → VAPI phone number
              → POST /voice/vapi-server   (VAPI serverUrl — returns assistant config)
              → POST /voice/vapi-llm      (VAPI custom-llm — each conversation turn)
              → Groq LLM → streaming response → VAPI TTS → speaks to patient

Outbound call → POST /voice/outbound      (staff triggers a call to a patient)
              → VAPI API makes the call using the same assistant config

Setup (one-time)
────────────────
1. Create a VAPI account at vapi.ai
2. Add a phone number in VAPI dashboard (~$2/month)
3. Set VAPI_API_KEY, VAPI_PHONE_NUMBER_ID, VOICE_BRANCH_SLUG in .env
4. In VAPI dashboard, set your number's Server URL to:
       https://<your-domain>/voice/vapi-server
5. VAPI will call /voice/vapi-llm automatically (configured in the assistant response)

No Twilio account needed. Free tier: 10 min/month.
"""
import json
import time
import uuid

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.branch import Branch
from app.models.doctor import Doctor

try:
    from groq import AsyncGroq
    _groq = AsyncGroq(api_key=settings.GROQ_API_KEY)
except Exception:
    _groq = None

router = APIRouter(prefix="/voice", tags=["Voice Agent"])
VAPI_BASE = "https://api.vapi.ai"
_LLM_MODEL = "llama-3.1-8b-instant"


# ── Clinic context ─────────────────────────────────────────────────────────────

def _load_clinic_context():
    slug = settings.VOICE_BRANCH_SLUG
    if not slug:
        return None, []
    db: Session = SessionLocal()
    try:
        branch = db.query(Branch).filter(
            Branch.slug == slug,
            Branch.is_active.is_(True),
        ).first()
        if not branch:
            return None, []
        doctors = db.query(Doctor).filter(
            Doctor.tenant_id == branch.tenant_id,
            Doctor.is_active.is_(True),
        ).all()
        return branch, list(doctors)
    finally:
        db.close()


def _build_system_prompt(branch, doctors: list) -> str:
    doc_lines = "\n".join(
        f"- Dr. {d.name} ({d.specialty}), fee: {d.fee or 'N/A'}, "
        f"days: {', '.join(t['day'] for t in (d.timings or []))}"
        for d in doctors
    ) or "No doctors currently listed."
    bot_name = branch.bot_name or f"{branch.name} AI"
    return (
        f"You are {bot_name}, the voice assistant for {branch.name} clinic.\n"
        "Keep replies SHORT — spoken aloud, under 35 words per turn.\n"
        "Help patients with: booking appointments, clinic hours, doctor info.\n\n"
        f"Available doctors:\n{doc_lines}\n\n"
        "Rules:\n"
        "- Always be polite and professional.\n"
        "- For bookings, collect: patient name, preferred doctor, preferred day and time.\n"
        "- Never share other patients' information.\n"
        "- Respond in plain spoken English only — no markdown, no lists, no symbols."
    )


def _assistant_config(base_url: str, branch, doctors: list) -> dict:
    """Build the VAPI assistant config dict (used for both inbound and outbound)."""
    clinic_name = branch.name if branch else "our clinic"
    first_msg = f"Hello, thank you for calling {clinic_name}. How can I help you today?"
    sys_prompt = _build_system_prompt(branch, doctors) if branch else "You are a helpful clinic assistant."

    return {
        "firstMessage": first_msg,
        "model": {
            "provider": "custom-llm",
            "url": f"{base_url}/voice/vapi-llm",
            "model": _LLM_MODEL,
            "systemPrompt": sys_prompt,
        },
        "voice": {
            "provider": "azure",
            "voiceId": "en-US-JennyNeural",
        },
        "endCallMessage": "Thank you for calling. Goodbye!",
        "maxDurationSeconds": 300,
        "silenceTimeoutSeconds": 10,
    }


# ── VAPI serverUrl endpoint ────────────────────────────────────────────────────

@router.post("/vapi-server")
async def vapi_server_url(request: Request):
    """VAPI calls this on each new inbound call to get the assistant config."""
    body = await request.json()
    msg_type = body.get("message", {}).get("type", "")

    if msg_type != "assistant-request":
        return {"status": "ok"}

    branch, doctors = _load_clinic_context()
    base_url = str(request.base_url).rstrip("/")
    return {"assistant": _assistant_config(base_url, branch, doctors)}


# ── Custom LLM endpoint (VAPI → Groq) ─────────────────────────────────────────

@router.post("/vapi-llm")
async def vapi_llm(request: Request):
    """VAPI sends OpenAI-compatible chat requests here; we forward to Groq.

    Supports both streaming (SSE) and non-streaming responses.
    """
    if not _groq:
        return JSONResponse(status_code=503, content={"error": "LLM not configured"})

    body = await request.json()
    messages = body.get("messages", [])
    model = body.get("model", _LLM_MODEL)
    do_stream = body.get("stream", False)

    if do_stream:
        async def sse():
            cid = f"chatcmpl-{uuid.uuid4().hex[:8]}"
            ts = int(time.time())
            try:
                stream = await _groq.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=120,
                    temperature=0.4,
                    stream=True,
                )
                async for chunk in stream:
                    content = chunk.choices[0].delta.content or ""
                    payload = {
                        "id": cid,
                        "object": "chat.completion.chunk",
                        "created": ts,
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {"content": content},
                            "finish_reason": None,
                        }],
                    }
                    yield f"data: {json.dumps(payload)}\n\n"
                # signal end
                done = {
                    "id": cid,
                    "object": "chat.completion.chunk",
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                }
                yield f"data: {json.dumps(done)}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as exc:
                yield f"data: {json.dumps({'error': str(exc)})}\n\n"

        return StreamingResponse(sse(), media_type="text/event-stream")

    # Non-streaming
    try:
        resp = await _groq.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=120,
            temperature=0.4,
        )
        content = resp.choices[0].message.content.strip()
    except Exception:
        content = "I'm having trouble right now. Please hold while I transfer you to our staff."

    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": content},
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


# ── Outbound calls ─────────────────────────────────────────────────────────────

class OutboundCallIn(BaseModel):
    patient_phone: str
    patient_name: str = ""
    first_message: str = ""


@router.post("/outbound")
async def make_outbound_call(data: OutboundCallIn, request: Request):
    """Trigger an outbound AI call to a patient via VAPI."""
    if not settings.VAPI_API_KEY or not settings.VAPI_PHONE_NUMBER_ID:
        return JSONResponse(
            status_code=503,
            content={"error": "Set VAPI_API_KEY and VAPI_PHONE_NUMBER_ID in .env"},
        )

    branch, doctors = _load_clinic_context()
    base_url = str(request.base_url).rstrip("/")
    assistant = _assistant_config(base_url, branch, doctors)

    if data.first_message:
        assistant["firstMessage"] = data.first_message
    elif data.patient_name:
        clinic = branch.name if branch else "your clinic"
        assistant["firstMessage"] = (
            f"Hello {data.patient_name}! This is {clinic} calling. "
            "I just wanted to follow up with you. Is this a good time?"
        )

    assistant["maxDurationSeconds"] = 180  # shorter for outbound

    payload = {
        "assistant": assistant,
        "phoneNumberId": settings.VAPI_PHONE_NUMBER_ID,
        "customer": {
            "number": data.patient_phone,
            "name": data.patient_name or "Patient",
        },
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{VAPI_BASE}/call/phone",
            json=payload,
            headers={"Authorization": f"Bearer {settings.VAPI_API_KEY}"},
        )

    if resp.status_code in (200, 201):
        return resp.json()
    return JSONResponse(status_code=resp.status_code, content=resp.json())


# ── Call history ───────────────────────────────────────────────────────────────

@router.get("/calls")
async def list_calls(limit: int = 25):
    """Fetch recent call records from VAPI."""
    if not settings.VAPI_API_KEY:
        return {"calls": [], "configured": False}

    params: dict = {"limit": limit}
    if settings.VAPI_PHONE_NUMBER_ID:
        params["phoneNumberId"] = settings.VAPI_PHONE_NUMBER_ID

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{VAPI_BASE}/call",
            params=params,
            headers={"Authorization": f"Bearer {settings.VAPI_API_KEY}"},
        )

    if resp.status_code == 200:
        return {"calls": resp.json(), "configured": True}
    return {"calls": [], "configured": True, "error": f"VAPI error {resp.status_code}"}


@router.get("/status")
def voice_status():
    """Return VAPI configuration status for the frontend."""
    return {
        "configured": bool(settings.VAPI_API_KEY and settings.VAPI_PHONE_NUMBER_ID),
        "branch_slug": settings.VOICE_BRANCH_SLUG or None,
        "has_api_key": bool(settings.VAPI_API_KEY),
        "has_phone_number": bool(settings.VAPI_PHONE_NUMBER_ID),
    }
