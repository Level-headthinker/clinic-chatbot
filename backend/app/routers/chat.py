# The most important router. Receives every message from the
# chat widget, passes it to the LLM, saves the conversation, and returns the AI reply.
# Also creates and manages chat sessions.

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import uuid
from app.database import get_db
from app.models.chat import ChatSession, Lead
from app.models.tenant import Tenant
from app.models.doctor import Doctor
from app.services.llm import get_ai_response, detect_language, extract_intent

router = APIRouter(prefix="/chat", tags=["Chat"])


class MessageRequest(BaseModel):
    session_token: Optional[str] = None
    tenant_slug: str
    message: str


class MessageResponse(BaseModel):
    session_token: str
    reply: str
    intent: str
    language: str


def get_doctors_info(doctors: list) -> str:
    if not doctors:
        return "No doctors available at the moment."
    info = []
    for d in doctors:
        info.append(
            f"- Dr. {d.name} | {d.specialty} | "
            f"{d.qualification} | Fee: {d.fee}"
        )
    return "\n".join(info)


@router.post("/message", response_model=MessageResponse)
def send_message(data: MessageRequest, db: Session = Depends(get_db)):

    tenant = db.query(Tenant).filter(
        Tenant.slug == data.tenant_slug,
        Tenant.is_active == True
    ).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Clinic not found")

    if data.session_token:
        session = db.query(ChatSession).filter(
            ChatSession.session_token == data.session_token,
            ChatSession.tenant_id == tenant.id
        ).first()
    else:
        session = None

    if not session:
        session = ChatSession(
            tenant_id=tenant.id,
            session_token=str(uuid.uuid4()),
            messages=[],
            language=detect_language(data.message)
        )
        db.add(session)
        db.flush()

    doctors = db.query(Doctor).filter(
        Doctor.tenant_id == tenant.id,
        Doctor.is_active == True
    ).all()

    clinic_info = (
        f"Clinic Name: {tenant.name}\n"
        f"Bot Name: {tenant.bot_name}\n"
        f"Welcome Message: {tenant.welcome_message}"
    )
    doctors_info = get_doctors_info(doctors)

    intent = extract_intent(data.message)
    language = detect_language(data.message)

    if language != "en":
        session.language = language

    ai_reply = get_ai_response(
        user_message=data.message,
        conversation_history=session.messages,
        bot_name=tenant.bot_name,
        clinic_info=clinic_info,
        doctors_info=doctors_info,
        patient_name=session.patient_name or "Not collected yet",
        patient_phone=session.patient_phone or "Not collected yet"
    )

    messages = list(session.messages)
    messages.append({"role": "user", "content": data.message})
    messages.append({"role": "assistant", "content": ai_reply})
    session.messages = messages
    session.current_intent = intent

    if session.patient_name and session.patient_phone:
        existing_lead = db.query(Lead).filter(
            Lead.phone == session.patient_phone,
            Lead.tenant_id == tenant.id
        ).first()
        if not existing_lead:
            lead = Lead(
                tenant_id=tenant.id,
                name=session.patient_name,
                phone=session.patient_phone,
                concern=data.message,
                source="chatbot"
            )
            db.add(lead)

    db.commit()

    return MessageResponse(
        session_token=session.session_token,
        reply=ai_reply,
        intent=intent,
        language=language
    )


@router.get("/session/{session_token}")
def get_session(session_token: str, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(
        ChatSession.session_token == session_token
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_token": session.session_token,
        "messages": session.messages,
        "language": session.language,
        "patient_name": session.patient_name,
        "patient_phone": session.patient_phone
    }