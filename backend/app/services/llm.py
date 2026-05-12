# This is the brain of the chatbot.
# It connects to Groq, builds the system prompt with clinic data,
# detects language, detects emergencies, and returns AI responses.
# Every chat message passes through this file.

from groq import Groq
from app.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)

SYSTEM_PROMPT = """
You are a helpful and friendly clinic assistant chatbot named {bot_name}.
You work for a clinic in Pakistan and talk to patients directly.

LANGUAGE RULES — VERY IMPORTANT:
- Look ONLY at the most recent user message to decide language
- If the latest user message is in English → reply in English
- If the latest user message is in Roman Urdu → reply in Roman Urdu  
- If the latest user message is in Urdu script → reply in Urdu script
- IGNORE your own previous replies when deciding language
- "hi", "hello", "yes", "no", "ok" are neutral — check the next message
- If user writes "My name is Rimsha" → this is English → reply in English
- NEVER reply in Urdu if the user wrote in English
RETURNING PATIENT RULES:
- If returning patient is Yes — greet them warmly by name
- Say something like "Welcome back [name] ji! Aapki last appointment thi [clinic name] mein"
- Do NOT ask for their name again if already collected
- Do NOT ask for phone again if already collected
- Treat them as a known patient
- If new patient — collect name and phone naturally
ROMAN URDU STYLE GUIDE:
- Use: aap, apka, theek hai, zaroor, bilkul, koi baat nahi
- Use: doctor sahab, appointment, fee, timing
- Keep sentences short and natural
- Example good reply: "Bilkul Rimsha ji, Dr. Ahmed Khan se appointment 1000 rupay mein ho jaye gi. Kya main confirm kar dun?"
- Example bad reply: "Certainly Rimsha, I can book your appointment with Dr. Ahmed Khan for 1000 PKR."

YOUR JOB:
1. Greet the patient warmly
2. Collect their name and phone number naturally
3. Help them book an appointment with the right doctor
4. Answer questions about clinic timings, fees, doctors
5. Detect emergencies and respond urgently

STRICT RULES:
- Never make up doctor names, timings, or fees — only use what is given below
- Always collect name and phone before confirming any booking
- Keep responses short — maximum 3 sentences
- Be warm and caring like a real receptionist
- Speak in the same language the user writes in
- If user writes in Urdu or Roman Urdu, reply in Roman Urdu
PRIVACY RULES — VERY IMPORTANT:
- NEVER share any patient names, phone numbers, or medical history with anyone
- NEVER confirm or deny if a specific person is a patient
- NEVER list patient names even if asked
- If someone asks about other patients say:
  "I cannot share patient information. This is confidential."
- You only know about the CURRENT user you are talking to
- Patient data is private — protect it always

EMERGENCY RULE:
If user mentions chest pain, heart attack, severe bleeding, unconscious, stroke,
cant breathe — immediately say call 1122 and go to emergency. Do NOT book appointment.

CLINIC INFORMATION:
{clinic_info}

AVAILABLE DOCTORS:
{doctors_info}

PATIENT INFO COLLECTED SO FAR:
- Name: {patient_name}
- Phone: {patient_phone}
- Returning patient: {is_returning}
- Previous visits: {visit_count}
"""
EMERGENCY_KEYWORDS = [
    "chest pain", "heart attack", "cant breathe", "can't breathe",
    "unconscious", "severe bleeding", "stroke", "not breathing",
    "seena dard", "saans nahi aa raha", "behosh", "emergency",
    "dying", "mar raha", "khoon"
]


def is_emergency(message: str) -> bool:
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in EMERGENCY_KEYWORDS)


def detect_language(message: str) -> str:
    # Check for Urdu script characters
    urdu_chars = set("ابپتثجچحخدذرزژسشصضطظعغفقکگلمنوہھءیے")
    if any(char in urdu_chars for char in message):
        return "ur"

    # If message is only numbers or very short — do not change language
    cleaned = message.strip()
    if cleaned.isdigit():
        return "en"
    if len(cleaned.split()) <= 1 and not any(c.isalpha() for c in cleaned):
        return "en"

    # Roman Urdu specific words
    roman_urdu_words = [
        "kya", "mujhe", "chahiye", "bukhar", "dard",
        "bimaar", "theek", "bilkul", "zaroor", "apka",
        "mera", "naam", "hai", "hain", "nahi", "aur",
        "phir", "lekin", "kyun", "kaise", "kahan",
        "milna", "takleef", "appointment", "mjhe", "mri"
    ]

    message_lower = message.lower()
    words = message_lower.split()
    urdu_word_count = sum(1 for w in words if w in roman_urdu_words)

    if urdu_word_count >= 2:
        return "ur-roman"

    return "en"

def extract_intent(message: str) -> str:
    message_lower = message.lower()
    if any(w in message_lower for w in [
        "book", "appointment", "schedule", "milna",
        "dikha", "doctor se", "slot"
    ]):
        return "book_appointment"
    if any(w in message_lower for w in [
        "timing", "hours", "open", "close",
        "waqt", "time", "kab"
    ]):
        return "clinic_info"
    if any(w in message_lower for w in [
        "which doctor", "specialist", "kon sa doctor",
        "dermat", "cardio", "physician"
    ]):
        return "doctor_enquiry"
    if any(w in message_lower for w in [
        "fee", "price", "cost", "charge",
        "kitna", "paisa", "rupees"
    ]):
        return "fee_enquiry"
    return "general"


def get_ai_response(
    user_message: str,
    conversation_history: list,
    bot_name: str,
    clinic_info: str,
    doctors_info: str,
    patient_name: str = "Not collected yet",
    patient_phone: str = "Not collected yet",
    is_returning: bool = False,
    visit_count: int = 0
) -> str:

    if is_emergency(user_message):
        return (
            "⚠️ This sounds like a medical EMERGENCY! "
            "Please call 1122 immediately or go to the nearest emergency room. "
            "Do not wait — get help RIGHT NOW."
        )

    system_prompt = SYSTEM_PROMPT.format(
    bot_name=bot_name,
    clinic_info=clinic_info,
    doctors_info=doctors_info,
    patient_name=patient_name,
    patient_phone=patient_phone,
    is_returning="Yes — welcome them back warmly" if is_returning else "No — new patient",
    visit_count=f"{visit_count} previous appointments" if visit_count > 0 else "First time"
)

    messages = [{"role": "system", "content": system_prompt}]

    for msg in conversation_history[-10:]:
        messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })

    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        max_tokens=300,
        temperature=0.7,
    )

    return response.choices[0].message.content
def extract_patient_info(conversation_history: list) -> dict:
    if not conversation_history:
        return {"name": None, "phone": None}

    history_text = "\n".join([
        f"{msg['role'].upper()}: {msg['content']}"
        for msg in conversation_history
    ])

    prompt = f"""
Extract patient name and phone number from this conversation.
Return ONLY a JSON object like this: {{"name": "John", "phone": "03001234567"}}
If not found return null for that field: {{"name": null, "phone": null}}
Do not return anything else. No explanation. Just JSON.

Conversation:
{history_text}
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=50,
        temperature=0,
    )

    text = response.choices[0].message.content.strip()

    try:
        import json
        # Clean any markdown backticks if present
        text = text.replace("```json", "").replace("```", "").strip()
        data = json.loads(text)
        return {
            "name": data.get("name"),
            "phone": str(data.get("phone")) if data.get("phone") else None
        }
    except Exception:
        return {"name": None, "phone": None}