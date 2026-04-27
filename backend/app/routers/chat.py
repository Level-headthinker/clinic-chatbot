from fastapi import APIRouter, Depends, HTTPException
from app.services.llm import get_ai_response, detect_language, extract_intent, extract_patient_info
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import uuid
import re
from datetime import datetime, timedelta
from app.database import get_db
from app.models.chat import ChatSession, Lead
from app.models.tenant import Tenant
from app.models.doctor import Doctor
from app.models.appointment import Appointment
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
        treatments = ", ".join(d.treatments) if d.treatments else "General"
        timings = ""
        if d.timings:
            timings = " | Timings: " + ", ".join([
                f"{t['day']} {t['from']}-{t['to']}"
                for t in d.timings
            ])
        info.append(
            f"- Dr. {d.name} | {d.specialty} | "
            f"Treats: {treatments} | "
            f"Fee: {d.fee}"
            f"{timings}"
        )
    return "\n".join(info)
def try_save_appointment(
    session: ChatSession,
    tenant_id,
    db: Session
):
    print(f"DEBUG INSIDE: name={session.patient_name} phone={session.patient_phone}")
    
    if not session.patient_name or not session.patient_phone:
        return

    existing = db.query(Appointment).filter(
        Appointment.patient_phone == session.patient_phone,
        Appointment.tenant_id == tenant_id,
        Appointment.status != "cancelled"
    ).first()
    if existing:
        print(f"DEBUG: Already exists for {session.patient_phone}")
        return

    doctor = db.query(Doctor).filter(
        Doctor.tenant_id == tenant_id,
        Doctor.is_active == True
    ).first()
    if not doctor:
        print("DEBUG: No doctor found")
        return

    print(f"DEBUG: Creating appointment for {session.patient_name}")

    slot = datetime.now().replace(
        hour=10, minute=0, second=0, microsecond=0
    ) + timedelta(days=1)

    appointment = Appointment(
        tenant_id=tenant_id,
        doctor_id=doctor.id,
        patient_name=session.patient_name,
        patient_phone=session.patient_phone,
        patient_concern=session.current_intent.replace("_", " ").title() if session.current_intent else "General Consultation",
        slot_datetime=slot,
        status="pending"
    )
    db.add(appointment)
    print(f"DEBUG: Done - appointment added")
def try_save_lead(
    session: ChatSession,
    tenant_id,
    db: Session
):
    if not session.patient_name or not session.patient_phone:
        return

    existing = db.query(Lead).filter(
        Lead.phone == session.patient_phone,
        Lead.tenant_id == tenant_id
    ).first()
    if existing:
        return

    lead = Lead(
            tenant_id=tenant_id,
            name=session.patient_name,
            phone=session.patient_phone,
            concern=session.messages[-2]["content"] if len(session.messages) >= 2 else "General Inquiry",
            source="chatbot",
            status="new"
        )
    db.add(lead)
@router.post("/message", response_model=MessageResponse)
def send_message(data: MessageRequest, db: Session = Depends(get_db)):

    # Find tenant
    tenant = db.query(Tenant).filter(
        Tenant.slug == data.tenant_slug,
        Tenant.is_active == True
    ).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Clinic not found")

    # Load or create session
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

# Use LLM to extract name and phone from full conversation
    if not session.patient_name or not session.patient_phone:
        # Build current messages including this new message
        current_messages = list(session.messages)
        current_messages.append({"role": "user", "content": data.message})
        
        info = extract_patient_info(current_messages)
        
        if info["name"] and not session.patient_name:
            session.patient_name = info["name"]
        if info["phone"] and not session.patient_phone:
            session.patient_phone = info["phone"]

    # Get doctors for this clinic
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

# Detect intent and language from USER MESSAGE ONLY
    intent = extract_intent(data.message)
    language = detect_language(data.message)

# Only change language if we got a clear signal
    # Numbers and single neutral words should not change language
    if language != "en" or session.language == "en":
        session.language = language
    session.current_intent = intent

    # Get AI response
    ai_reply = get_ai_response(
        user_message=data.message,
        conversation_history=session.messages,
        bot_name=tenant.bot_name,
        clinic_info=clinic_info,
        doctors_info=doctors_info,
        patient_name=session.patient_name or "Not collected yet",
        patient_phone=session.patient_phone or "Not collected yet"
    )

    # Save messages to session
    messages = list(session.messages)
    messages.append({"role": "user", "content": data.message})
    messages.append({"role": "assistant", "content": ai_reply})
    session.messages = messages

# Auto save lead when we have name and phone
    try_save_lead(session, tenant.id, db)

    # Only save appointment if patient confirmed
    confirmation_words = [
        "yes", "confirm", "book", "ok", "okay", "sure",
        "haan", "ji", "bilkul", "zaroor", "theek hai",
        "ho jaye", "kar do", "book kar", "yes please"
    ]
    user_confirmed = any(
        word in data.message.lower() 
        for word in confirmation_words
    )

    if user_confirmed:
        try_save_appointment(session, tenant.id, db)
        # Mark lead as converted when appointment confirmed
        lead = db.query(Lead).filter(
            Lead.phone == session.patient_phone,
            Lead.tenant_id == tenant.id
        ).first()
        if lead:
            lead.status = "converted"

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