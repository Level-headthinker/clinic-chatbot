"""AI Voice Agent via Twilio.

Architecture:
  Incoming call → Twilio webhook POST /voice/incoming
  → TwiML <Gather input="speech"> collects speech
  → POST /voice/respond with transcript
  → Groq LLM (same clinic context as chat agent)
  → TwiML <Say> speaks the response back

Each HTTP request is a separate coroutine — concurrent calls are handled
naturally by the async FastAPI event loop with no extra infrastructure.

To wire up:
  1. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER in .env
  2. In Twilio console, point your number's Voice webhook to:
       https://<your-domain>/voice/incoming
  3. Set VOICE_BRANCH_SLUG in .env to route calls to the correct branch/clinic.
"""
import os
from fastapi import APIRouter, Form, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.branch import Branch
from app.models.doctor import Doctor
from app.services.conversation_logger import log_output_flag
from app.config import settings

try:
    from groq import Groq
    _groq = Groq(api_key=settings.GROQ_API_KEY)
except Exception:
    _groq = None

router = APIRouter(prefix="/voice", tags=["Voice Agent"])

VOICE_BRANCH_SLUG = os.environ.get("VOICE_BRANCH_SLUG", "")


def _twiml(body: str) -> Response:
    return Response(content=body, media_type="application/xml")


def _build_system_prompt(branch: Branch, doctors: list) -> str:
    doctor_list = "\n".join(
        f"- Dr. {d.name} ({d.specialty}), fee: {d.fee or 'N/A'}, "
        f"available: {', '.join(t['day'] for t in (d.timings or []))}"
        for d in doctors
    ) or "No doctors currently listed."

    return f"""You are {branch.bot_name or branch.name + ' AI'}, the voice assistant for {branch.name} clinic.
Keep replies SHORT — spoken out loud, under 40 words per turn.
You help patients with: booking appointments, clinic hours, doctor information, directions.

Available doctors:
{doctor_list}

Rules:
- Always be polite and professional.
- If asked to book an appointment, collect: patient name, preferred doctor, preferred day/time.
- If you cannot help, say you will transfer to staff.
- Never share other patients' information.
- Respond only in plain spoken English (no markdown, no lists, no symbols)."""


def _get_clinic_context():
    """Load branch + doctors from DB for the configured VOICE_BRANCH_SLUG."""
    db: Session = SessionLocal()
    try:
        branch = db.query(Branch).filter(
            Branch.slug == VOICE_BRANCH_SLUG,
            Branch.is_active == True,
        ).first()
        if not branch:
            return None, []
        doctors = db.query(Doctor).filter(
            Doctor.tenant_id == branch.tenant_id,
            Doctor.is_active == True,
        ).all()
        return branch, doctors
    finally:
        db.close()


@router.post("/incoming")
def voice_incoming(request: Request):
    """Twilio calls this when a patient dials the clinic number.
    Greets the caller and opens a speech gather loop.
    """
    branch, _ = _get_clinic_context()
    clinic_name = branch.name if branch else "the clinic"
    bot_name = (branch.bot_name if branch else None) or "AI Assistant"

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="Polly.Joanna">
    Hello, thank you for calling {clinic_name}. I am {bot_name}, your AI assistant.
    How can I help you today?
  </Say>
  <Gather input="speech" action="/voice/respond" method="POST"
          speechTimeout="auto" language="en-US" timeout="5">
  </Gather>
  <Say voice="Polly.Joanna">I didn't catch that. Please call again and I'll be happy to help.</Say>
</Response>"""
    return _twiml(twiml)


@router.post("/respond")
def voice_respond(SpeechResult: str = Form(default=""), Confidence: str = Form(default="0")):
    """Twilio posts the transcribed speech here. We run it through the LLM and reply."""
    if not SpeechResult.strip():
        twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="Polly.Joanna">I'm sorry, I couldn't hear you clearly. Could you please repeat that?</Say>
  <Gather input="speech" action="/voice/respond" method="POST"
          speechTimeout="auto" language="en-US" timeout="5">
  </Gather>
</Response>"""
        return _twiml(twiml)

    branch, doctors = _get_clinic_context()

    if not _groq or not branch:
        twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="Polly.Joanna">
    I'm sorry, our AI assistant is temporarily unavailable. Please call back shortly or visit us in person.
  </Say>
  <Hangup/>
</Response>"""
        return _twiml(twiml)

    system_prompt = _build_system_prompt(branch, doctors)

    try:
        completion = _groq.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": SpeechResult},
            ],
            max_tokens=120,
            temperature=0.4,
        )
        reply = completion.choices[0].message.content.strip()
    except Exception as exc:
        log_output_flag(
            session_token="voice",
            output_text=str(exc),
            branch_id=branch.id if branch else None,
        )
        reply = "I'm having trouble processing that right now. Please hold while I transfer you to our staff."

    # Sanitise for TwiML — strip any XML special chars
    safe_reply = reply.replace("&", "and").replace("<", "").replace(">", "")

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="Polly.Joanna">{safe_reply}</Say>
  <Gather input="speech" action="/voice/respond" method="POST"
          speechTimeout="auto" language="en-US" timeout="5">
  </Gather>
  <Say voice="Polly.Joanna">Is there anything else I can help you with? Goodbye.</Say>
  <Hangup/>
</Response>"""
    return _twiml(twiml)


@router.post("/status")
def voice_status(CallStatus: str = Form(default=""), CallDuration: str = Form(default="0")):
    """Twilio status callback — logs completed calls."""
    return {"status": "received", "call_status": CallStatus, "duration": CallDuration}
