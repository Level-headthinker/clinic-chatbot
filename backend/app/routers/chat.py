from datetime import datetime, timedelta
import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.appointment import Appointment
from app.models.chat import ChatSession, Lead
from app.models.doctor import Doctor
from app.models.tenant import Tenant
from app.models.user import User
from app.services.conversation_logger import log_input_flag, log_output_flag
from app.services.email import send_booking_notification, send_lead_notification
from app.services.auth import get_current_user
from app.services.input_guard import run_input_guard
from app.services.llm import (
    detect_language,
    extract_intent,
    extract_patient_info,
    get_ai_response,
    is_emergency,
    _message_may_contain_patient_info,
)
from app.services.output_guard import run_output_guard

router = APIRouter(prefix="/chat", tags=["Chat"])

BOOKED_STATUSES = ["pending", "confirmed"]
CONFIRMATION_WORDS = [
    "yes", "confirm", "book", "ok", "okay", "sure",
    "haan", "han", "ji", "bilkul", "zaroor", "theek hai",
    "ho jaye", "kar do", "book kar", "yes please"
]
WEEKDAY_BY_NAME = {
    "monday": 0, "tuesday": 1, "wednesday": 2,
    "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6,
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


def display_doctor_name(doctor):
    name = (doctor.name or "").strip()
    return name if name.lower().startswith("dr") else f"Dr. {name}"


def get_doctors_info(doctors):
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
            f"Treats: {treatments} | Fee: {doctor.fee or 'Not set'}{timings}"
        )
    return "\n".join(info)


def parse_time(value):
    if not value:
        return None
    value = value.strip().upper().replace(".", "")
    for fmt in ("%I:%M %p", "%I %p", "%H:%M", "%H"):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    return None


def normalize_datetime(value):
    return value.replace(tzinfo=None) if value.tzinfo else value


def generate_doctor_slots(doctor, tenant_id, db, days_ahead=14, max_slots=3):
    now = datetime.now()
    window_end = now + timedelta(days=days_ahead)
    booked_rows = db.query(Appointment.slot_datetime).filter(
        Appointment.tenant_id == tenant_id,
        Appointment.doctor_id == doctor.id,
        Appointment.status.in_(BOOKED_STATUSES),
        Appointment.slot_datetime >= now,
        Appointment.slot_datetime < window_end,
    ).all()
    booked_slots = {normalize_datetime(r[0]) for r in booked_rows if r[0]}
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


def doctor_match_score(doctor, text):
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
        t = str(treatment).lower()
        if t and t in text:
            score += 8
        for word in re.findall(r"[a-z0-9]+", t):
            if len(word) > 3 and word in words:
                score += 2
    for keyword, aliases in SPECIALTY_KEYWORDS.items():
        if keyword in specialty and any(a in text for a in aliases):
            score += 5
    return score


def build_booking_search_text(session, user_message):
    user_messages = [
        msg.get("content", "")
        for msg in (session.messages or [])[-8:]
        if msg.get("role") == "user"
    ]
    user_messages.append(user_message)
    if session.current_intent:
        user_messages.append(session.current_intent.replace("_", " "))
    return " ".join(user_messages)


def find_booking_options(doctors, tenant_id, db, search_text, max_doctors=2):
    options = []
    for doctor in doctors:
        slots = generate_doctor_slots(doctor, tenant_id, db)
        if not slots:
            continue
        options.append({"doctor": doctor, "slots": slots, "score": doctor_match_score(doctor, search_text)})
    options.sort(key=lambda o: (-o["score"], o["slots"][0]))
    return options[:max_doctors]


def format_slot(slot):
    return slot.strftime("%A, %d %B %Y at %I:%M %p")


def is_confirmation_message(message):
    return any(w in message.lower() for w in CONFIRMATION_WORDS)


def booking_suggestion_reply(options, language):
    if not options:
        return ("Filhal koi available slot nahi mil raha. Clinic se direct contact kar lein."
                if language in ["ur", "ur-roman"] else
                "I could not find an available slot right now. Please contact the clinic directly.")
    lines = [f"{display_doctor_name(o['doctor'])}: {format_slot(o['slots'][0])}" for o in options]
    if language in ["ur", "ur-roman"]:
        return "Available slot: " + " | ".join(lines) + ". Pehla slot confirm karne ke liye yes reply kar dein."
    return "Available slot: " + " | ".join(lines) + ". Reply yes to confirm the first slot."


def appointment_confirmation_reply(doctor, slot, language):
    if language in ["ur", "ur-roman"]:
        return (f"Done, appointment request {display_doctor_name(doctor)} ke sath "
                f"{format_slot(slot)} ke liye save ho gayi hai. Clinic staff confirmation ke liye contact karega.")
    return (f"Done, your appointment request with {display_doctor_name(doctor)} "
            f"for {format_slot(slot)} has been saved. The clinic staff will contact you to confirm.")


def appointment_error_reply(reason, language):
    roman = language in ["ur", "ur-roman"]
    if reason == "missing_patient":
        return "Appointment book karne ke liye apna naam aur phone number share kar dein." if roman else \
               "Please share your name and phone number before I book an appointment."
    if reason == "active_appointment":
        return "Aapki pending ya confirmed appointment pehle se mojood hai." if roman else \
               "You already have a pending or confirmed appointment."
    if reason == "no_slots":
        return "Filhal koi available slot nahi mil raha. Clinic se direct contact kar lein." if roman else \
               "I could not find an available slot right now. Please contact the clinic directly."
    return "Appointment save nahi ho saki." if roman else "I could not save the appointment."


def concern_from_session(session):
    for msg in reversed(session.messages or []):
        content = msg.get("content", "").strip()
        if msg.get("role") != "user" or not content:
            continue
        if is_confirmation_message(content):
            continue
        if re.fullmatch(r"[\d+\-\s()]{7,}", content):
            continue
        return content[:500]
    return (session.current_intent.replace("_", " ").title()
            if session.current_intent else "General Consultation")


def tenant_notification_email(tenant_id, db):
    admin = db.query(User).filter(
        User.tenant_id == tenant_id,
        User.is_active == True,
        User.role.in_(["admin", "superadmin"]),
    ).order_by(User.created_at.asc()).first()
    return admin.email if admin else ""


def try_save_appointment(session, tenant_id, db, doctors, search_text):
    if not session.patient_name or not session.patient_phone:
        return None, None, None, "missing_patient"
    active = db.query(Appointment).filter(
        Appointment.patient_phone == session.patient_phone,
        Appointment.tenant_id == tenant_id,
        Appointment.status.in_(BOOKED_STATUSES)
    ).first()
    if active:
        return None, None, None, "active_appointment"
    options = find_booking_options(doctors, tenant_id, db, search_text, max_doctors=1)
    if not options:
        return None, None, None, "no_slots"
    doctor = options[0]["doctor"]
    slot = options[0]["slots"][0]
    appointment = Appointment(
        tenant_id=tenant_id, doctor_id=doctor.id,
        patient_name=session.patient_name, patient_phone=session.patient_phone,
        patient_concern=concern_from_session(session), slot_datetime=slot, status="pending"
    )
    db.add(appointment)
    return appointment, doctor, slot, None


def try_save_lead(session, tenant_id, db) -> bool:
    if not session.patient_name or not session.patient_phone:
        return False
    existing = db.query(Lead).filter(
        Lead.phone == session.patient_phone, Lead.tenant_id == tenant_id
    ).first()
    if existing:
        return False
    lead = Lead(
        tenant_id=tenant_id, name=session.patient_name, phone=session.patient_phone,
        concern=concern_from_session(session), source="chatbot", status="new"
    )
    db.add(lead)
    return True


# ════════════════════════════════════════════════════════════
# MAIN CHAT ENDPOINT
# Phases 1 + 2 + 4 all active in this single function
# ════════════════════════════════════════════════════════════

@router.post("/message", response_model=MessageResponse)
def send_message(data: MessageRequest, request: Request, db: Session = Depends(get_db)):

    # ── PHASE 1: INPUT GUARD ─────────────────────────────────
    client_ip = request.client.host if request.client else "unknown"
    guard_key = data.session_token or f"pre-session:{data.tenant_slug}:{client_ip}"
    guard = run_input_guard(data.message, guard_key)

    if not guard.allowed:
        lang = detect_language(data.message)

        # ── PHASE 4: LOG INPUT BLOCK ─────────────────────────
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

    # ── Resolve tenant ───────────────────────────────────────
    tenant = db.query(Tenant).filter(
        Tenant.slug == data.tenant_slug, Tenant.is_active == True
    ).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Clinic not found")

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
            session_token=str(uuid.uuid4()),
            messages=[],
            language=detect_language(clean_message)
        )
        db.add(session)
        db.flush()

    if (not session.patient_name or not session.patient_phone) and \
            _message_may_contain_patient_info(clean_message):
        current_messages = list(session.messages or [])
        current_messages.append({"role": "user", "content": clean_message})
        info = extract_patient_info(current_messages)
        if info["name"] and not session.patient_name:
            session.patient_name = info["name"]
        if info["phone"] and not session.patient_phone:
            session.patient_phone = info["phone"]

    is_returning = False
    visit_count = 0
    if session.patient_phone:
        from app.models.patient import Patient
        prev = db.query(Appointment).filter(
            Appointment.patient_phone == session.patient_phone,
            Appointment.tenant_id == tenant.id
        ).count()
        existing_patient = db.query(Patient).filter(
            Patient.phone == session.patient_phone,
            Patient.tenant_id == tenant.id
        ).first()
        is_returning = prev > 0 or existing_patient is not None
        visit_count = prev
        if existing_patient and not session.patient_name:
            session.patient_name = existing_patient.name

    doctors = db.query(Doctor).filter(
        Doctor.tenant_id == tenant.id, Doctor.is_active == True
    ).all()

    clinic_info = (
        f"Clinic Name: {tenant.name}\nBot Name: {tenant.bot_name}\n"
        f"Welcome Message: {tenant.welcome_message}\n"
        f"Clinic Timings: Monday to Saturday, 9am to 9pm\nEmergency: Call 1122"
    )

    user_confirmed = is_confirmation_message(clean_message)
    intent = extract_intent(clean_message)
    if intent == "general" and user_confirmed and session.current_intent:
        intent = session.current_intent

    language = detect_language(clean_message)
    session.language = language
    session.current_intent = intent

    # ── PHASE 2: AI RESPONSE (hardened prompt + output guard) ─
    raw_ai_reply = get_ai_response(
        user_message=clean_message,
        conversation_history=session.messages or [],
        bot_name=tenant.bot_name,
        clinic_info=clinic_info,
        doctors_info=get_doctors_info(doctors),
        patient_name=session.patient_name or "Not collected yet",
        patient_phone=session.patient_phone or "Not collected yet",
        is_returning=is_returning,
        visit_count=visit_count
    )

    guarded_reply = run_output_guard(raw_ai_reply, clean_message, language)
    safe_reply = guarded_reply.final_response

    # ── PHASE 4: LOG OUTPUT INTERCEPTIONS ────────────────────
    if guarded_reply.was_modified and guarded_reply.should_log:
        if guarded_reply.flag:
            out_flag = guarded_reply.flag
        elif is_emergency(clean_message):
            out_flag = "emergency_override"
        elif any(p in raw_ai_reply.lower() for p in ["probably have", "sounds like", "take 500mg"]):
            out_flag = "medical_advice"
        elif any(p in raw_ai_reply.lower() for p in ["here are the patients", "patient 1:"]):
            out_flag = "patient_leak"
        else:
            out_flag = "output_intercepted"

        log_output_flag(
            db=db,
            flag_type=out_flag,
            flagged_message=clean_message,
            intercepted_response=raw_ai_reply,
            safe_response=safe_reply,
            session_token=session.session_token,
            tenant_id=tenant.id,
        )

    ai_reply = safe_reply

    messages = list(session.messages or [])
    messages.append({"role": "user", "content": clean_message})
    messages.append({"role": "assistant", "content": ai_reply})
    session.messages = messages

    new_lead = try_save_lead(session, tenant.id, db)

    booking_text = build_booking_search_text(session, clean_message)
    if (intent == "book_appointment" and not user_confirmed
            and session.patient_name and session.patient_phone
            and not is_emergency(clean_message)):
        options = find_booking_options(doctors, tenant.id, db, booking_text)
        ai_reply = f"{ai_reply}\n\n{booking_suggestion_reply(options, language)}"

    appointment, doctor, slot = None, None, None
    if user_confirmed and intent == "book_appointment" and not is_emergency(clean_message):
        appointment, doctor, slot, error = try_save_appointment(
            session=session, tenant_id=tenant.id, db=db,
            doctors=doctors, search_text=booking_text
        )
        if appointment and doctor and slot:
            ai_reply = appointment_confirmation_reply(doctor, slot, language)
            lead = db.query(Lead).filter(
                Lead.phone == session.patient_phone, Lead.tenant_id == tenant.id
            ).first()
            if lead:
                lead.status = "converted"
        else:
            ai_reply = appointment_error_reply(error or "unknown", language)

    messages[-1] = {"role": "assistant", "content": ai_reply}
    session.messages = messages

    # Notifications fire only after a successful commit — never for unsaved records.
    try:
        db.commit()
        if new_lead or (appointment and doctor and slot):
            concern = concern_from_session(session)
            admin_email = tenant_notification_email(tenant.id, db)
            if new_lead:
                send_lead_notification(
                    patient_name=session.patient_name,
                    patient_phone=session.patient_phone,
                    concern=concern,
                    clinic_name=tenant.name,
                    to_email=admin_email,
                )
            if appointment and doctor and slot:
                send_booking_notification(
                    patient_name=session.patient_name,
                    patient_phone=session.patient_phone,
                    patient_concern=appointment.patient_concern or "General",
                    doctor_name=display_doctor_name(doctor),
                    slot=format_slot(slot),
                    clinic_name=tenant.name,
                    to_email=admin_email,
                )
    except IntegrityError:
        db.rollback()
        ai_reply = appointment_error_reply("active_appointment", language)
    return MessageResponse(
        session_token=session.session_token,
        reply=ai_reply, intent=intent, language=language
    )


@router.get("/session/{session_token}")
def get_session(
    session_token: str,
    tenant_slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant = db.query(Tenant).filter(
        Tenant.slug == tenant_slug, Tenant.is_active == True
    ).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Clinic not found")
    if not current_user.is_superadmin and current_user.tenant_id != tenant.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    session = db.query(ChatSession).filter(
        ChatSession.session_token == session_token,
        ChatSession.tenant_id == tenant.id
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
