"""Shared conversation + booking brain.

This is the single source of truth for a conversational turn — used by every
channel so they behave identically:

  • Web chat widget        → routers/chat.py  (send_message)
  • WhatsApp text + voice  → routers/whatsapp.py
  • (future) phone calls

A caller resolves the branch/tenant/session for its channel, then hands the
patient's text to ``handle_turn`` which does the rest: patient-info extraction,
returning-patient detection, the LLM reply (hardened prompt), output guard,
lead capture, slot suggestion, appointment booking on confirmation, the DB
commit, and admin notifications.

Previously this logic lived inline inside ``chat.py::send_message`` — so the web
chat could book but WhatsApp could not. Extracting it here is what lets voice
notes and WhatsApp text book through the exact same code path.
"""
from datetime import datetime, timedelta
import re

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from app.models.appointment import Appointment
from app.models.chat import Lead
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.user import User
from app.services.conversation_logger import log_output_flag
from app.services.email import send_booking_notification, send_lead_notification
from app.services.llm import (
    detect_language,
    extract_intent,
    extract_patient_info,
    get_ai_response,
    is_emergency,
    _message_may_contain_patient_info,
)
from app.services.output_guard import run_output_guard
from app.services.knowledge_retrieval import retrieve_knowledge, format_knowledge

BOOKED_STATUSES = ["pending", "confirmed"]
# Whole-word/phrase matching only. "book" is deliberately NOT here — it's a
# booking-INTENT keyword; treating it as a confirmation made "I want to book an
# appointment" instantly book the top slot without ever showing options. And
# substring matching made "ok" fire inside "looking"/"booked".
_CONFIRMATION_RE = re.compile(
    r"\b(yes|confirm|ok|okay|sure|haan|han|ji|jee|bilkul|zaroor"
    r"|theek hai|ho jaye|kar do|yes please|g kar do|haan kar do)\b",
    re.IGNORECASE,
)
# A confirmation word inside a NEGATED sentence is not a confirmation —
# "not just confirm and tell me…" must NOT auto-book. Catches English +
# Roman Urdu negations.
_NEGATION_RE = re.compile(
    r"\b(not|don'?t|never|no|cannot|can'?t|without|nahi|nai|mat)\b",
    re.IGNORECASE,
)
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
    msg = message or ""
    if _NEGATION_RE.search(msg):
        return False
    return bool(_CONFIRMATION_RE.search(msg))


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


_PHONE_IN_MSG = re.compile(r"(\+92|92|0)3[0-9]{9}|\b\d{10,11}\b")


def _last10(phone: str) -> str:
    """Last 10 digits — the channel-agnostic identity of a PK mobile.
    923001234567, 03001234567, +92 300 1234567 all → '3001234567'."""
    digits = re.sub(r"\D", "", phone or "")
    return digits[-10:] if len(digits) >= 10 else ""


def _format_pk_phone(phone: str) -> str:
    """Normalize a typed number to 03XXXXXXXXX for storage."""
    local = _last10(phone)
    return "0" + local if local else (phone or "")


def detect_alternate_phone(primary_phone: str, message: str):
    """If `message` contains a phone number DIFFERENT from primary_phone, return
    it (formatted) — e.g. the patient is booking for a family member. Same number
    (any format) → None, so we never store a duplicate of the primary."""
    if not primary_phone:
        return None
    match = _PHONE_IN_MSG.search(message or "")
    if not match:
        return None
    typed = match.group(0)
    if _last10(typed) and _last10(typed) != _last10(primary_phone):
        return _format_pk_phone(typed)
    return None


def _name_matches(a: str, b: str, threshold: int = 85) -> bool:
    """True if two names are the same person (case/spacing/spelling tolerant).
    Used to decide reuse-vs-new when the same number books again."""
    a = (a or "").strip().lower()
    b = (b or "").strip().lower()
    if not a or not b:
        return False
    if a == b:
        return True
    try:
        from rapidfuzz import fuzz
        return fuzz.token_sort_ratio(a, b) >= threshold
    except Exception:
        return a == b


def upsert_patient_for_booking(db, tenant_id, branch_id, name, phone):
    """Find-or-create the Patient record for a booking.

    - Same number + matching name  → reuse that patient (a returning patient);
      bump booking_count so the repeat booking is visible.
    - Same number + DIFFERENT name → create a NEW patient (e.g. a family member
      booking from the same WhatsApp number) — never overwrite the first person.
    - New number                   → create a new patient.

    Returns ``(patient, is_returning)``.
    """
    from datetime import timezone
    local = _last10(phone)
    candidates = []
    if local:
        candidates = db.query(Patient).filter(
            Patient.tenant_id == tenant_id,
            Patient.is_active == True,
            Patient.phone.ilike(f"%{local}"),
        ).all()
        # ilike suffix can over-match (e.g. shared prefixes) — confirm last-10.
        candidates = [p for p in candidates if _last10(p.phone) == local]

    match = next((p for p in candidates if _name_matches(p.name, name)), None)
    now = datetime.now(timezone.utc)
    if match:
        match.booking_count = (match.booking_count or 0) + 1
        match.last_booking_at = now
        return match, True

    patient = Patient(
        tenant_id=tenant_id,
        primary_branch_id=branch_id,
        name=name,
        phone=_format_pk_phone(phone),
        booking_count=1,
        last_booking_at=now,
    )
    db.add(patient)
    db.flush()
    return patient, False


def concern_from_session(session):
    for msg in reversed(session.messages or []):
        content = msg.get("content", "").strip()
        if msg.get("role") != "user" or not content:
            continue
        if is_confirmation_message(content):
            continue
        if re.fullmatch(r"[\d+\-\s()]{7,}", content):
            continue
        if _PHONE_IN_MSG.search(content):  # skip contact-info messages that contain a phone
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


def try_save_appointment(session, tenant_id, branch_id, db, doctors, search_text):
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
    # Create/update the patient record (returning-patient aware) and link the
    # appointment to it, so every booking lands in the Patients list and a repeat
    # patient's booking_count goes up instead of silently duplicating.
    patient, _returning = upsert_patient_for_booking(
        db, tenant_id, branch_id, session.patient_name, session.patient_phone
    )
    appointment = Appointment(
        tenant_id=tenant_id, branch_id=branch_id, doctor_id=doctor.id,
        patient_id=patient.id,
        patient_name=session.patient_name, patient_phone=session.patient_phone,
        alternate_phone=session.alternate_phone,
        patient_concern=concern_from_session(session), slot_datetime=slot, status="pending"
    )
    db.add(appointment)
    return appointment, doctor, slot, None


def try_save_lead(session, tenant_id, branch_id, db) -> bool:
    if not session.patient_name or not session.patient_phone:
        return False
    existing = db.query(Lead).filter(
        Lead.phone == session.patient_phone, Lead.tenant_id == tenant_id
    ).first()
    if existing:
        return False
    lead = Lead(
        tenant_id=tenant_id, branch_id=branch_id, name=session.patient_name,
        phone=session.patient_phone, alternate_phone=session.alternate_phone,
        concern=concern_from_session(session),
        source="chatbot", status="new"
    )
    db.add(lead)
    return True


# ════════════════════════════════════════════════════════════
# THE SHARED BRAIN — one conversational turn, all channels
# ════════════════════════════════════════════════════════════

def handle_turn(db, branch, tenant, session, clean_message, *, modality: str = "text"):
    """Run one conversational turn and return ``(reply, intent, language)``.

    The caller must have already resolved ``branch``/``tenant`` and a persisted
    ``session`` (it is committed here). ``clean_message`` should already be
    input-guard sanitized. ``modality`` is "text" or "voice" — reserved for
    channel-specific shaping (voice replies are kept short by the prompt itself).
    """
    # ── Patient info extraction ──────────────────────────────
    if (not session.patient_name or not session.patient_phone) and \
            _message_may_contain_patient_info(clean_message):
        current_messages = list(session.messages or [])
        current_messages.append({"role": "user", "content": clean_message})
        info = extract_patient_info(current_messages)
        if info["name"] and not session.patient_name:
            session.patient_name = info["name"]
        if info["phone"] and not session.patient_phone:
            session.patient_phone = info["phone"]

    # Alternate booking number: once we know the patient's primary (WhatsApp/
    # first) number, if they type a DIFFERENT one, keep it as a secondary
    # contact under the same patient name. Same number → ignored (saved once).
    if session.patient_phone and not session.alternate_phone:
        alt = detect_alternate_phone(session.patient_phone, clean_message)
        if alt:
            session.alternate_phone = alt

    # ── Returning-patient lookup ─────────────────────────────
    # Match on the last 10 digits so 0300…, 92300…, +92 300… all resolve to the
    # same person regardless of how the number was stored.
    is_returning = False
    visit_count = 0
    if session.patient_phone:
        local = _last10(session.patient_phone)
        prev = db.query(Appointment).filter(
            Appointment.patient_phone.ilike(f"%{local}") if local else
            Appointment.patient_phone == session.patient_phone,
            Appointment.tenant_id == tenant.id
        ).count()
        existing_patient = db.query(Patient).filter(
            Patient.tenant_id == tenant.id,
            Patient.is_active == True,
            Patient.phone.ilike(f"%{local}") if local else
            Patient.phone == session.patient_phone,
        ).first()
        is_returning = prev > 0 or existing_patient is not None
        # Prefer the patient's tracked booking count; fall back to appointment count.
        visit_count = (existing_patient.booking_count if existing_patient and existing_patient.booking_count
                       else prev)
        # Remember the name only if the patient hasn't given one THIS conversation
        # (a new name stated now wins → it may be a different family member).
        if existing_patient and not session.patient_name:
            session.patient_name = existing_patient.name

    doctors = db.query(Doctor).filter(
        Doctor.tenant_id == tenant.id,
        Doctor.is_active == True,
        or_(Doctor.branch_id == branch.id, Doctor.branch_id.is_(None)),
    ).all()

    bot_name = branch.bot_name or tenant.bot_name
    welcome_msg = branch.welcome_message or tenant.welcome_message

    phone_val = branch.phone if branch and branch.phone else "Not configured"
    hours_val = branch.working_hours if branch and branch.working_hours else "Not configured"
    address_parts = [p for p in [
        branch.address if branch else None,
        branch.city if branch else None,
    ] if p]
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

    user_confirmed = is_confirmation_message(clean_message)
    intent = extract_intent(clean_message)
    if intent == "general" and user_confirmed and session.current_intent:
        intent = session.current_intent

    language = detect_language(clean_message, fallback=session.language or "en")
    session.language = language
    session.current_intent = intent

    # ── Knowledge-base retrieval (lightweight RAG) ───────────
    kb_entries = retrieve_knowledge(db, tenant.id, clean_message, k=3)
    kb_text = format_knowledge(kb_entries)

    # ── AI response (hardened prompt + output guard) ─────────
    raw_ai_reply = get_ai_response(
        user_message=clean_message,
        conversation_history=session.messages or [],
        bot_name=bot_name,
        clinic_info=clinic_info,
        doctors_info=get_doctors_info(doctors),
        patient_name=session.patient_name or "Not collected yet",
        patient_phone=session.patient_phone or "Not collected yet",
        is_returning=is_returning,
        visit_count=visit_count,
        language=language,
        tone=getattr(tenant, "bot_tone", None) or "warm",
        knowledge_base=kb_text,
    )

    guarded_reply = run_output_guard(raw_ai_reply, clean_message, language)
    safe_reply = guarded_reply.final_response

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
            branch_id=branch.id,
        )

    ai_reply = safe_reply

    messages = list(session.messages or [])
    messages.append({"role": "user", "content": clean_message})
    messages.append({"role": "assistant", "content": ai_reply})
    session.messages = messages

    new_lead = try_save_lead(session, tenant.id, branch.id, db)

    booking_text = build_booking_search_text(session, clean_message)
    if (intent == "book_appointment" and not user_confirmed
            and session.patient_name and session.patient_phone
            and not is_emergency(clean_message)):
        options = find_booking_options(doctors, tenant.id, db, booking_text)
        ai_reply = f"{ai_reply}\n\n{booking_suggestion_reply(options, language)}"

    appointment, doctor, slot = None, None, None
    if user_confirmed and intent == "book_appointment" and not is_emergency(clean_message):
        appointment, doctor, slot, error = try_save_appointment(
            session=session, tenant_id=tenant.id, branch_id=branch.id, db=db,
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

    return ai_reply, intent, language
