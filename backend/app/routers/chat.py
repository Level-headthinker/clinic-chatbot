from datetime import datetime, timedelta
import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.appointment import Appointment
from app.models.chat import ChatSession, Lead
from app.models.doctor import Doctor
from app.models.tenant import Tenant
from app.services.email import send_booking_notification, send_lead_notification
from app.services.llm import (
    detect_language,
    extract_intent,
    extract_patient_info,
    get_ai_response,
    is_emergency,
)

router = APIRouter(prefix="/chat", tags=["Chat"])

BOOKED_STATUSES = ["pending", "confirmed"]
CONFIRMATION_WORDS = [
    "yes", "confirm", "book", "ok", "okay", "sure",
    "haan", "han", "ji", "bilkul", "zaroor", "theek hai",
    "ho jaye", "kar do", "book kar", "yes please"
]
WEEKDAY_BY_NAME = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}
SPECIALTY_KEYWORDS = {
    "cardio": ["heart", "chest", "bp", "blood pressure", "cardio"],
    "dermat": ["skin", "rash", "acne", "dermat"],
    "dent": ["tooth", "teeth", "dental", "dentist"],
    "pedia": ["child", "baby", "kids", "pediatric"],
    "gyn": ["pregnancy", "pregnant", "gyn", "women"],
    "ortho": ["bone", "joint", "fracture", "ortho"],
    "physician": ["fever", "flu", "cough", "diabetes", "general"],
}


class MessageRequest(BaseModel):
    session_token: Optional[str] = None
    tenant_slug: str
    message: str


class MessageResponse(BaseModel):
    session_token: str
    reply: str
    intent: str
    language: str


def display_doctor_name(doctor: Doctor) -> str:
    name = (doctor.name or "").strip()
    return name if name.lower().startswith("dr") else f"Dr. {name}"


def get_doctors_info(doctors: list[Doctor]) -> str:
    if not doctors:
        return "No doctors available at the moment."

    info = []
    for doctor in doctors:
        treatments = ", ".join(doctor.treatments) if doctor.treatments else "General"
        timings = ""
        if doctor.timings:
            timings = " | Timings: " + ", ".join([
                f"{t.get('day')} {t.get('from')}-{t.get('to')}"
                for t in doctor.timings
            ])
        info.append(
            f"- {display_doctor_name(doctor)} | {doctor.specialty} | "
            f"Treats: {treatments} | "
            f"Fee: {doctor.fee or 'Not set'}"
            f"{timings}"
        )
    return "\n".join(info)


def parse_time(value: Optional[str]):
    if not value:
        return None

    value = value.strip().upper().replace(".", "")
    for fmt in ("%I:%M %p", "%I %p", "%H:%M", "%H"):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    return None


def normalize_datetime(value: datetime) -> datetime:
    return value.replace(tzinfo=None) if value.tzinfo else value


def generate_doctor_slots(
    doctor: Doctor,
    tenant_id,
    db: Session,
    days_ahead: int = 14,
    max_slots: int = 3
) -> list[datetime]:
    now = datetime.now()
    window_end = now + timedelta(days=days_ahead)
    booked_rows = db.query(Appointment.slot_datetime).filter(
        Appointment.tenant_id == tenant_id,
        Appointment.doctor_id == doctor.id,
        Appointment.status.in_(BOOKED_STATUSES),
        Appointment.slot_datetime >= now,
        Appointment.slot_datetime < window_end,
    ).all()
    booked_slots = {
        normalize_datetime(row[0])
        for row in booked_rows
        if row[0] is not None
    }

    slots = []
    for timing in doctor.timings or []:
        weekday = WEEKDAY_BY_NAME.get(str(timing.get("day", "")).strip().lower())
        start_time = parse_time(timing.get("from"))
        end_time = parse_time(timing.get("to"))
        if weekday is None or not start_time or not end_time:
            continue

        for offset in range(days_ahead + 1):
            day = now.date() + timedelta(days=offset)
            if day.weekday() != weekday:
                continue

            slot = datetime.combine(day, start_time)
            end = datetime.combine(day, end_time)
            while slot < end:
                if slot > now and slot not in booked_slots:
                    slots.append(slot)
                slot += timedelta(minutes=30)

    return sorted(slots)[:max_slots]


def doctor_match_score(doctor: Doctor, text: str) -> int:
    text = text.lower()
    words = set(re.findall(r"[a-z0-9]+", text))
    score = 0

    specialty = (doctor.specialty or "").lower()
    if specialty and specialty in text:
        score += 10
    for word in re.findall(r"[a-z0-9]+", specialty):
        if len(word) > 3 and word in words:
            score += 3

    for treatment in doctor.treatments or []:
        treatment_text = str(treatment).lower()
        if treatment_text and treatment_text in text:
            score += 8
        for word in re.findall(r"[a-z0-9]+", treatment_text):
            if len(word) > 3 and word in words:
                score += 2

    for keyword, aliases in SPECIALTY_KEYWORDS.items():
        if keyword in specialty and any(alias in text for alias in aliases):
            score += 5

    return score


def build_booking_search_text(session: ChatSession, user_message: str) -> str:
    user_messages = [
        msg.get("content", "")
        for msg in (session.messages or [])[-8:]
        if msg.get("role") == "user"
    ]
    user_messages.append(user_message)
    if session.current_intent:
        user_messages.append(session.current_intent.replace("_", " "))
    return " ".join(user_messages)


def find_booking_options(
    doctors: list[Doctor],
    tenant_id,
    db: Session,
    search_text: str,
    max_doctors: int = 2
) -> list[dict]:
    options = []
    for doctor in doctors:
        slots = generate_doctor_slots(doctor, tenant_id, db)
        if not slots:
            continue
        options.append({
            "doctor": doctor,
            "slots": slots,
            "score": doctor_match_score(doctor, search_text),
        })

    options.sort(key=lambda option: (-option["score"], option["slots"][0]))
    return options[:max_doctors]


def format_slot(slot: datetime) -> str:
    return slot.strftime("%A, %d %B %Y at %I:%M %p")


def is_confirmation_message(message: str) -> bool:
    message_lower = message.lower()
    return any(word in message_lower for word in CONFIRMATION_WORDS)


def booking_suggestion_reply(options: list[dict], language: str) -> str:
    if not options:
        if language in ["ur", "ur-roman"]:
            return "Filhal koi available slot nahi mil raha. Clinic se direct contact kar lein."
        return "I could not find an available slot right now. Please contact the clinic directly."

    lines = []
    for option in options:
        doctor = option["doctor"]
        first_slot = option["slots"][0]
        lines.append(f"{display_doctor_name(doctor)}: {format_slot(first_slot)}")

    if language in ["ur", "ur-roman"]:
        return (
            "Available slot: "
            + " | ".join(lines)
            + ". Pehla slot confirm karne ke liye yes reply kar dein."
        )
    return (
        "Available slot: "
        + " | ".join(lines)
        + ". Reply yes to confirm the first slot."
    )


def appointment_confirmation_reply(doctor: Doctor, slot: datetime, language: str) -> str:
    if language in ["ur", "ur-roman"]:
        return (
            f"Done, appointment request {display_doctor_name(doctor)} ke sath "
            f"{format_slot(slot)} ke liye save ho gayi hai. Clinic staff confirmation ke liye contact karega."
        )
    return (
        f"Done, your appointment request with {display_doctor_name(doctor)} "
        f"for {format_slot(slot)} has been saved. The clinic staff will contact you to confirm."
    )


def appointment_error_reply(reason: str, language: str) -> str:
    roman = language in ["ur", "ur-roman"]
    if reason == "missing_patient":
        return (
            "Appointment book karne ke liye apna naam aur phone number share kar dein."
            if roman else
            "Please share your name and phone number before I book an appointment."
        )
    if reason == "active_appointment":
        return (
            "Aapki pending ya confirmed appointment pehle se mojood hai."
            if roman else
            "You already have a pending or confirmed appointment."
        )
    if reason == "no_slots":
        return (
            "Filhal koi available slot nahi mil raha. Clinic se direct contact kar lein."
            if roman else
            "I could not find an available slot right now. Please contact the clinic directly."
        )
    return "Appointment save nahi ho saki." if roman else "I could not save the appointment."


def concern_from_session(session: ChatSession) -> str:
    for msg in reversed(session.messages or []):
        content = msg.get("content", "").strip()
        if msg.get("role") != "user" or not content:
            continue
        if is_confirmation_message(content):
            continue
        if re.fullmatch(r"[\d+\-\s()]{7,}", content):
            continue
        return content[:500]
    return (
        session.current_intent.replace("_", " ").title()
        if session.current_intent else
        "General Consultation"
    )


def try_save_appointment(
    session: ChatSession,
    tenant_id,
    db: Session,
    tenant_name: str,
    doctors: list[Doctor],
    search_text: str
) -> tuple[Optional[Appointment], Optional[Doctor], Optional[datetime], Optional[str]]:
    if not session.patient_name or not session.patient_phone:
        return None, None, None, "missing_patient"

    active_appointment = db.query(Appointment).filter(
        Appointment.patient_phone == session.patient_phone,
        Appointment.tenant_id == tenant_id,
        Appointment.status.in_(BOOKED_STATUSES)
    ).first()
    if active_appointment:
        return None, None, None, "active_appointment"

    options = find_booking_options(doctors, tenant_id, db, search_text, max_doctors=1)
    if not options:
        return None, None, None, "no_slots"

    doctor = options[0]["doctor"]
    slot = options[0]["slots"][0]
    appointment = Appointment(
        tenant_id=tenant_id,
        doctor_id=doctor.id,
        patient_name=session.patient_name,
        patient_phone=session.patient_phone,
        patient_concern=concern_from_session(session),
        slot_datetime=slot,
        status="pending"
    )
    db.add(appointment)

    send_booking_notification(
        patient_name=session.patient_name,
        patient_phone=session.patient_phone,
        patient_concern=appointment.patient_concern or "General",
        doctor_name=doctor.name,
        slot=format_slot(slot),
        clinic_name=tenant_name
    )
    return appointment, doctor, slot, None


def try_save_lead(session: ChatSession, tenant_id, db: Session, tenant_name: str):
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
        concern=concern_from_session(session),
        source="chatbot",
        status="new"
    )
    db.add(lead)

    send_lead_notification(
        patient_name=session.patient_name,
        patient_phone=session.patient_phone,
        concern=lead.concern or "General Inquiry",
        clinic_name=tenant_name
    )


@router.post("/message", response_model=MessageResponse)
def send_message(data: MessageRequest, db: Session = Depends(get_db)):
    tenant = db.query(Tenant).filter(
        Tenant.slug == data.tenant_slug,
        Tenant.is_active == True
    ).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Clinic not found")

    session = None
    if data.session_token:
        session = db.query(ChatSession).filter(
            ChatSession.session_token == data.session_token,
            ChatSession.tenant_id == tenant.id
        ).first()

    if not session:
        session = ChatSession(
            tenant_id=tenant.id,
            session_token=str(uuid.uuid4()),
            messages=[],
            language=detect_language(data.message)
        )
        db.add(session)
        db.flush()

    if not session.patient_name or not session.patient_phone:
        current_messages = list(session.messages or [])
        current_messages.append({"role": "user", "content": data.message})
        info = extract_patient_info(current_messages)
        if info["name"] and not session.patient_name:
            session.patient_name = info["name"]
        if info["phone"] and not session.patient_phone:
            session.patient_phone = info["phone"]

    is_returning = False
    visit_count = 0
    if session.patient_phone:
        from app.models.patient import Patient

        prev_appointments = db.query(Appointment).filter(
            Appointment.patient_phone == session.patient_phone,
            Appointment.tenant_id == tenant.id
        ).count()

        existing_patient = db.query(Patient).filter(
            Patient.phone == session.patient_phone,
            Patient.tenant_id == tenant.id
        ).first()

        is_returning = prev_appointments > 0 or existing_patient is not None
        visit_count = prev_appointments
        if existing_patient and not session.patient_name:
            session.patient_name = existing_patient.name

    doctors = db.query(Doctor).filter(
        Doctor.tenant_id == tenant.id,
        Doctor.is_active == True
    ).all()

    clinic_info = (
        f"Clinic Name: {tenant.name}\n"
        f"Bot Name: {tenant.bot_name}\n"
        f"Welcome Message: {tenant.welcome_message}\n"
        f"Clinic Timings: Monday to Saturday, 9am to 9pm\n"
        f"Emergency: Call 1122"
    )
    doctors_info = get_doctors_info(doctors)

    user_confirmed = is_confirmation_message(data.message)
    intent = extract_intent(data.message)
    if intent == "general" and user_confirmed and session.current_intent:
        intent = session.current_intent

    language = detect_language(data.message)
    if language != "en" or session.language == "en":
        session.language = language
    session.current_intent = intent

    ai_reply = get_ai_response(
        user_message=data.message,
        conversation_history=session.messages or [],
        bot_name=tenant.bot_name,
        clinic_info=clinic_info,
        doctors_info=doctors_info,
        patient_name=session.patient_name or "Not collected yet",
        patient_phone=session.patient_phone or "Not collected yet",
        is_returning=is_returning,
        visit_count=visit_count
    )

    messages = list(session.messages or [])
    messages.append({"role": "user", "content": data.message})
    messages.append({"role": "assistant", "content": ai_reply})
    session.messages = messages

    try_save_lead(session, tenant.id, db, tenant.name)

    booking_text = build_booking_search_text(session, data.message)
    if (
        intent == "book_appointment"
        and not user_confirmed
        and session.patient_name
        and session.patient_phone
        and not is_emergency(data.message)
    ):
        options = find_booking_options(doctors, tenant.id, db, booking_text)
        ai_reply = f"{ai_reply}\n\n{booking_suggestion_reply(options, language)}"
        messages[-1] = {"role": "assistant", "content": ai_reply}
        session.messages = messages

    if user_confirmed and intent == "book_appointment" and not is_emergency(data.message):
        appointment, doctor, slot, error = try_save_appointment(
            session=session,
            tenant_id=tenant.id,
            db=db,
            tenant_name=tenant.name,
            doctors=doctors,
            search_text=booking_text
        )
        if appointment and doctor and slot:
            ai_reply = appointment_confirmation_reply(doctor, slot, language)
            lead = db.query(Lead).filter(
                Lead.phone == session.patient_phone,
                Lead.tenant_id == tenant.id
            ).first()
            if lead:
                lead.status = "converted"
        else:
            ai_reply = appointment_error_reply(error or "unknown", language)
        messages[-1] = {"role": "assistant", "content": ai_reply}
        session.messages = messages

    db.commit()

    return MessageResponse(
        session_token=session.session_token,
        reply=ai_reply,
        intent=intent,
        language=language
    )


@router.get("/session/{session_token}")
def get_session(
    session_token: str,
    tenant_slug: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(ChatSession).filter(
        ChatSession.session_token == session_token
    )
    if tenant_slug:
        tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Clinic not found")
        query = query.filter(ChatSession.tenant_id == tenant.id)

    session = query.first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    response = {
        "session_token": session.session_token,
        "messages": session.messages,
        "language": session.language,
    }
    if tenant_slug:
        response.update({
            "patient_name": session.patient_name,
            "patient_phone": session.patient_phone
        })
    return response
