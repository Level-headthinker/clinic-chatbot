# This is the brain of the chatbot.
# It connects to Groq, builds the system prompt with clinic data,
# detects language, detects emergencies, and returns AI responses.
# Every chat message passes through this file.

from groq import Groq
from app.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)

SYSTEM_PROMPT = """
You are a helpful clinic assistant chatbot named {bot_name}.
Your job is to:
1. Help patients book appointments with doctors
2. Answer questions about the clinic and services
3. Collect patient name and phone number naturally in conversation
4. Detect emergencies and respond urgently

STRICT RULES:
- Always be polite, caring, and professional
- Keep responses short — maximum 3 sentences
- Never make up doctor names or timings — only use what is given to you below
- Always collect name and phone before booking
- Speak in the same language the user writes in
- If user writes in Urdu or Roman Urdu, reply in Roman Urdu

EMERGENCY RULE:
If user mentions chest pain, heart attack, can't breathe, severe bleeding,
unconscious, stroke — immediately tell them to call 1122 and go to emergency.
Do NOT book appointment for emergencies.

CLINIC INFORMATION:
{clinic_info}

AVAILABLE DOCTORS:
{doctors_info}

PATIENT INFO COLLECTED SO FAR:
- Name: {patient_name}
- Phone: {patient_phone}
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
    urdu_script = set("ابپتثجچحخدذرزژسشصضطظعغفقکگلمنوہھءیے")
    roman_urdu_words = [
        "kya", "hai", "mujhe", "chahiye", "doctor", "bukhar",
        "dard", "bimaar", "appointment", "milna", "takleef"
    ]
    if any(char in urdu_script for char in message):
        return "ur"
    if any(word in message.lower() for word in roman_urdu_words):
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
    patient_phone: str = "Not collected yet"
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
        patient_phone=patient_phone
    )

    messages = [{"role": "system", "content": system_prompt}]

    for msg in conversation_history[-10:]:
        messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })

    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model="llama-3.1-70b-versatile",
        messages=messages,
        max_tokens=300,
        temperature=0.7,
    )

    return response.choices[0].message.content