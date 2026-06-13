# ============================================================
# OUTPUT GUARD — Phase 3 of AI Safety Guardrails
# ============================================================
# This runs AFTER the LLM produces a response, BEFORE it is
# sent to the user. Think of it as the last line of defence.
#
# It does 5 things in order:
#   1. Emergency override  — if the LLM missed an emergency,
#      replace its response with the correct emergency message
#   2. Medical advice detection  — catch diagnosis/medicine
#      suggestions the LLM smuggled through anyway
#   3. Length cap  — hard-truncate responses that are too long
#   4. Disclaimer injection  — append a disclaimer when the
#      response touches medical/health adjacent topics
#   5. Safe fallback  — if the response is empty or garbled,
#      return a clean fallback instead of an empty bubble
#
# Returns a GuardedOutput so chat.py knows what happened.
#
# Usage in chat.py (after get_ai_response):
#   result = run_output_guard(ai_reply, user_message, language)
#   final_reply = result.final_response
#   if result.was_modified:
#       log_for_review(result)
# ============================================================

import re
from dataclasses import dataclass, field
from typing import Optional


# ── Result object ────────────────────────────────────────────
@dataclass
class GuardedOutput:
    final_response: str          # What gets sent to the user
    was_modified: bool           # True if guard changed anything
    modification_reason: Optional[str] = None  # Why it was changed
    flag: Optional[str] = None   # Category for logging
    should_log: bool = False     # True = save for admin review


# ── Configuration ────────────────────────────────────────────
class OutputGuardConfig:
    # Hard character cap on any single response
    MAX_RESPONSE_LENGTH = 800

    # Truncation suffix added when a response is cut
    TRUNCATION_SUFFIX = "... [براہ کرم مزید معلومات کے لیے کلینک سے رابطہ کریں / Please contact the clinic for more details.]"

    # Disclaimer appended when health-adjacent language is detected
    # but the response does NOT cross into forbidden advice territory
    HEALTH_DISCLAIMER = (
        "\n\n⚕️ _Note: I am a clinic assistant, not a doctor. "
        "Please consult our doctor for any medical concerns._"
    )
    HEALTH_DISCLAIMER_UR = (
        "\n\n⚕️ _نوٹ: میں ڈاکٹر نہیں ہوں۔ طبی مسائل کے لیے براہ کرم ڈاکٹر سے ملیں۔_"
    )
    HEALTH_DISCLAIMER_ROMAN = (
        "\n\n⚕️ _Note: Main doctor nahi hoon. "
        "Tibbi masail ke liye doctor se zaroor milein._"
    )


# ── Emergency messages (mirrors llm.py, kept in sync) ────────
_EMERGENCY_RESPONSE = {
    "en": (
        "⚠️ This sounds like a medical EMERGENCY! "
        "Please call 1122 immediately or go to the nearest emergency room. "
        "Do not wait — get help RIGHT NOW."
    ),
    "ur": (
        "⚠️ یہ میڈیکل ایمرجنسی لگ رہی ہے۔ "
        "براہ کرم فوراً 1122 پر کال کریں یا قریبی ایمرجنسی جائیں۔ "
        "انتظار نہ کریں۔"
    ),
    "ur-roman": (
        "⚠️ Yeh medical emergency lag rahi hai. "
        "Foran 1122 par call karein ya qareebi emergency mein jayen. "
        "Intizar na karein."
    ),
}

# Emergency signals to check in the *LLM output* (not user input).
# The LLM might echo the user's emergency words back in its reply
# without actually escalating — this catches that case.
_EMERGENCY_OUTPUT_SIGNALS = [
    r"chest\s+pain", r"heart\s+attack", r"can'?t\s+breathe",
    r"severe\s+bleeding", r"\bstroke\b", r"not\s+breathing",
    r"seena\s+dard", r"saans\s+nahi", r"\bbehosh\b",
]
_COMPILED_EMERGENCY = [
    re.compile(p, re.IGNORECASE) for p in _EMERGENCY_OUTPUT_SIGNALS
]

# The LLM should already call 1122 in emergencies.
# If it does, do NOT flag — it handled it correctly.
_EMERGENCY_ALREADY_HANDLED = re.compile(r"1122", re.IGNORECASE)


# ── Step 1: Emergency override ───────────────────────────────
def check_emergency_in_output(
    response: str,
    user_message: str,
    language: str
) -> Optional[GuardedOutput]:
    """
    If the LLM response contains emergency language but did NOT
    include the 1122 escalation, override the whole response.

    This catches the edge case where the LLM acknowledges the
    emergency but responds softly (e.g. "please book an appointment
    for your chest pain") instead of escalating.
    """
    has_emergency_signal = any(
        p.search(response) or p.search(user_message)
        for p in _COMPILED_EMERGENCY
    )
    already_handled = _EMERGENCY_ALREADY_HANDLED.search(response)

    if has_emergency_signal and not already_handled:
        lang = language if language in _EMERGENCY_RESPONSE else "en"
        return GuardedOutput(
            final_response=_EMERGENCY_RESPONSE[lang],
            was_modified=True,
            modification_reason="Emergency detected in output but not escalated by LLM",
            flag="emergency_override",
            should_log=True
        )
    return None


# ── Medical advice patterns ───────────────────────────────────
# These match output that looks like actual medical advice —
# the kind the LLM should never produce.
#
# Design: we look for the combination of a medical authority
# marker ("you should", "I recommend", "take", "prescribed")
# with a clinical noun (medicine, dosage, diagnosis phrase).
# This avoids false positives on harmless mentions.

_MEDICAL_ADVICE_PATTERNS = [
    # Recommending specific medicines or doses
    (r"\b(take|use|try)\s+\w+\s*(mg|ml|tablet|capsule|syrup|injection|dose)\b", "medicine_dose"),
    (r"\b(panadol|paracetamol|ibuprofen|amoxicillin|metformin|insulin|aspirin|omeprazole)\b", "named_medicine"),

    # Diagnosis language
    (r"\b(you\s+probably\s+have|you\s+likely\s+have)\s+\w+", "diagnosis"),
    # "you have …" is diagnosis language, EXCEPT for benign scheduling nouns —
    # "you have an appointment / booking / slot" is a normal receptionist reply,
    # not medical advice.
    (r"\b(you\s+(have|may\s+have|might\s+have|are\s+suffering\s+from))\s+"
     r"(?!an?\s+(appointment|booking|slot|visit|consultation|question|query|reservation)\b)\w+", "diagnosis"),
    (r"\b(it\s+(sounds|seems|looks)\s+like\s+(you\s+have|a\s+case\s+of))\b", "diagnosis"),
    (r"\b(this\s+(sounds|seems|looks)\s+like\s+(a|an)?\s*\w+)", "diagnosis"),
    (r"\byour\s+(condition|symptoms?|problem)\s+(is|are|suggest)\b", "diagnosis"),

    # Telling patient symptoms are fine / not serious
    (r"\b(nothing\s+to\s+worry|just\s+a\s+(cold|fever|minor)|not\s+serious|you('ll|'re)\s+(be\s+)?fine)\b", "false_reassurance"),

    # Interpreting tests
    (r"\b(your\s+(results?|report|test|blood\s+test|CBC|ECG)\s+(shows?|indicate|suggest|means?))\b", "test_interpretation"),

    # Prescribing behaviour
    (r"\b(I\s+recommend\s+(taking|using)|you\s+should\s+take)\s+\w+", "prescription"),

    # Roman Urdu medical advice
    (r"\b(yeh\s+(dawai|dawa|medicine)\s+lein|yeh\s+tablet\s+khayein)\b", "medicine_urdu"),
    (r"\b(aap\s+ko\s+\w+\s+(hai|hogi|ho\s+sakti))\b", "diagnosis_urdu"),
]

_COMPILED_MEDICAL = [
    (re.compile(p, re.IGNORECASE), flag)
    for p, flag in _MEDICAL_ADVICE_PATTERNS
]

_PATIENT_LEAK_PATTERNS = [
    (r"\bhere\s+are\s+the\s+patients?\b", "patient_list"),
    (r"\bpatients?\s*:\s*[\w\s,.-]+", "patient_list"),
    (r"\bpatient\s+\d+\s*:", "patient_enumeration"),
    (r"\b(list|show|share)\s+(all\s+)?patients?\b", "patient_list"),

    # Third-party confirmation — the bot must never confirm/deny that a named
    # person (he/she/they/<Name>) is a patient or has an appointment. The 8b
    # model hallucinated "I can confirm she has an appointment today"; these
    # catch that. Scoped to third person so the genuine booking reply to the
    # current user ("your appointment is confirmed") is NOT flagged.
    (r"\b(he|she|they)\s+(has|have|had|is\s+having)\s+(an?\s+)?appointment", "third_party_appointment"),
    (r"\b(is|was)\s+(a\s+|an\s+)?(registered\s+|existing\s+|our\s+)?patient\b(?!\s+(portal|record|information|assistant|details))", "third_party_patient"),
    (r"\bcan\s+(confirm|see|tell)\s+(you\s+)?that\s+\w+\s+(is|was|has|had|booked)\b", "third_party_confirmation"),
    (r"\byes,?\s+\w+\s+(is|was)\s+(a\s+|an\s+)?patient\b", "third_party_patient"),
]

_COMPILED_PATIENT_LEAKS = [
    (re.compile(p, re.IGNORECASE), flag)
    for p, flag in _PATIENT_LEAK_PATTERNS
]

_PATIENT_LEAK_OVERRIDE = {
    "en": "I cannot share patient information. This is confidential.",
    "ur": "میں مریضوں کی معلومات شیئر نہیں کر سکتا۔ یہ خفیہ ہے۔",
    "ur-roman": "Main patient information share nahi kar sakta. Yeh confidential hai.",
}

# Safe fallback when medical advice is detected
_MEDICAL_OVERRIDE = {
    "en": (
        "I'm not able to give medical advice. "
        "Please book an appointment so our doctor can help you properly."
    ),
    "ur": (
        "میں طبی مشورہ دینے کے قابل نہیں ہوں۔ "
        "براہ کرم اپائنٹمنٹ بک کریں تاکہ ڈاکٹر آپ کی مدد کر سکیں۔"
    ),
    "ur-roman": (
        "Main tibbi mashwara dene ke qabil nahi hoon. "
        "Appointment book karein taake doctor aapki madad kar saken."
    ),
}


def check_medical_advice(response: str, language: str) -> Optional[GuardedOutput]:
    """
    Scan the LLM output for medical advice patterns.
    If found, replace the entire response with a safe redirect.
    Returns None if the response is clean.
    """
    for pattern, flag in _COMPILED_MEDICAL:
        if pattern.search(response):
            lang = language if language in _MEDICAL_OVERRIDE else "en"
            return GuardedOutput(
                final_response=_MEDICAL_OVERRIDE[lang],
                was_modified=True,
                modification_reason=f"Medical advice detected: {flag}",
                flag=f"medical_advice:{flag}",
                should_log=True
            )
    return None


def check_patient_leak(response: str, language: str) -> Optional[GuardedOutput]:
    """Replace any response that appears to expose patient records."""
    for pattern, flag in _COMPILED_PATIENT_LEAKS:
        if pattern.search(response):
            lang = language if language in _PATIENT_LEAK_OVERRIDE else "en"
            return GuardedOutput(
                final_response=_PATIENT_LEAK_OVERRIDE[lang],
                was_modified=True,
                modification_reason=f"Patient data leak detected: {flag}",
                flag="patient_leak",
                should_log=True
            )
    return None


# ── Step 3: Length cap ───────────────────────────────────────
def check_length(response: str) -> Optional[GuardedOutput]:
    """
    Hard-truncate responses longer than MAX_RESPONSE_LENGTH.
    Truncation happens at the last sentence boundary before the
    limit, not mid-sentence, to keep the output readable.
    Returns None if within limit.
    """
    if len(response) <= OutputGuardConfig.MAX_RESPONSE_LENGTH:
        return None

    # Cut at the last sentence boundary before the limit so the final text
    # NEVER exceeds MAX_RESPONSE_LENGTH (the old code appended a 99-char
    # bilingual suffix after cutting at the limit, overshooting the cap).
    cutoff = response[:OutputGuardConfig.MAX_RESPONSE_LENGTH]
    last_period = max(
        cutoff.rfind("."),
        cutoff.rfind("۔"),   # Urdu full stop
        cutoff.rfind("!"),
        cutoff.rfind("?"),
    )
    if last_period > OutputGuardConfig.MAX_RESPONSE_LENGTH // 2:
        truncated = cutoff[:last_period + 1]
    else:
        # No usable sentence boundary — hard cut with an ellipsis, still capped.
        truncated = cutoff[: OutputGuardConfig.MAX_RESPONSE_LENGTH - 3].rstrip() + "..."

    return GuardedOutput(
        final_response=truncated,
        was_modified=True,
        modification_reason=f"Response truncated from {len(response)} to {len(truncated)} chars",
        flag="too_long",
        should_log=False   # Long responses are annoying, not dangerous
    )


# ── Health-adjacent disclaimer patterns ──────────────────────
# These are NOT medical advice — but the LLM used health language
# (symptoms, conditions) in a context that warrants a disclaimer.
# We append the disclaimer rather than replacing the response.

_DISCLAIMER_TRIGGERS = [
    r"\b(symptom|fever|pain|cough|nausea|vomit|dizziness|fatigue)\b",
    r"\b(bukhar|dard|khansi|ulti|chakkar)\b",          # Roman Urdu
    r"\b(specialist|treatment|diagnosis|condition)\b",
    r"\b(sugar|diabetes|blood\s+pressure|BP)\b",
]
_COMPILED_DISCLAIMER = [
    re.compile(p, re.IGNORECASE) for p in _DISCLAIMER_TRIGGERS
]

# Do NOT add a disclaimer if the response already contains one
_DISCLAIMER_ALREADY_PRESENT = re.compile(r"(not\s+a\s+doctor|tibbi\s+mashwara|doctor\s+nahi)", re.IGNORECASE)


def inject_disclaimer(response: str, language: str) -> Optional[GuardedOutput]:
    """
    Append a language-appropriate disclaimer if the response
    touches health-adjacent language but is not outright advice.
    Skips if a disclaimer is already present.
    Returns None if no disclaimer needed.
    """
    if _DISCLAIMER_ALREADY_PRESENT.search(response):
        return None

    triggered = any(p.search(response) for p in _COMPILED_DISCLAIMER)
    if not triggered:
        return None

    if language == "ur":
        disclaimer = OutputGuardConfig.HEALTH_DISCLAIMER_UR
    elif language == "ur-roman":
        disclaimer = OutputGuardConfig.HEALTH_DISCLAIMER_ROMAN
    else:
        disclaimer = OutputGuardConfig.HEALTH_DISCLAIMER

    return GuardedOutput(
        final_response=response + disclaimer,
        was_modified=True,
        modification_reason="Health-adjacent language detected; disclaimer appended",
        flag="disclaimer_injected",
        should_log=False
    )


# ── Step 5: Safe fallback ────────────────────────────────────
_FALLBACK = {
    "en": "I'm sorry, I couldn't process that. Please try again or call the clinic directly.",
    "ur": "معذرت، میں یہ سمجھ نہیں سکا۔ براہ کرم دوبارہ کوشش کریں یا کلینک کو کال کریں۔",
    "ur-roman": "Maafi chahta hoon, samajh nahi saka. Dobara koshish karein ya clinic ko call karein.",
}


def check_empty_response(response: str, language: str) -> Optional[GuardedOutput]:
    """
    If the LLM returned an empty, whitespace-only, or nonsensical
    (under 3 chars) response, substitute a safe fallback.
    """
    if not response or len(response.strip()) < 3:
        lang = language if language in _FALLBACK else "en"
        return GuardedOutput(
            final_response=_FALLBACK[lang],
            was_modified=True,
            modification_reason="LLM returned empty or near-empty response",
            flag="empty_response",
            should_log=True
        )
    return None


# ── Main entry point ─────────────────────────────────────────
def run_output_guard(
    response: str,
    user_message: str,
    language: str
) -> GuardedOutput:
    """
    Run all output checks in order. Call this in chat.py after
    get_ai_response() and before returning the reply to the user.

    Order matters:
      1. Empty check  — no point running other checks on nothing
      2. Emergency    — highest safety priority, override first
      3. Medical      — replace bad advice before truncating
      4. Length       — truncate after content is validated
      5. Disclaimer   — only append if everything above passed

    Usage in chat.py:
        ai_reply = get_ai_response(...)
        guarded = run_output_guard(ai_reply, clean_message, language)
        final_reply = guarded.final_response
        if guarded.should_log:
            # hand off to Phase 6 logging
            pass

    Args:
        response:     Raw text from get_ai_response()
        user_message: The sanitized user message (for emergency re-check)
        language:     "en" | "ur" | "ur-roman" from detect_language()

    Returns:
        GuardedOutput with the safe final_response to send.
    """

    # Step 1 — empty / garbled response
    empty_result = check_empty_response(response, language)
    if empty_result:
        return empty_result

    # Step 2 — emergency override
    emergency_result = check_emergency_in_output(response, user_message, language)
    if emergency_result:
        return emergency_result

    # Step 3 — medical advice replacement
    medical_result = check_medical_advice(response, language)
    if medical_result:
        return medical_result

    # Step 4 — patient data leak replacement
    patient_leak_result = check_patient_leak(response, language)
    if patient_leak_result:
        return patient_leak_result

    # Step 5 — length cap (run on potentially clean response)
    length_result = check_length(response)
    if length_result:
        # After truncation, re-run disclaimer check on the shorter text
        disclaimer_after_truncation = inject_disclaimer(
            length_result.final_response, language
        )
        if disclaimer_after_truncation:
            # Merge: keep truncation reason, use disclaimer-appended text
            return GuardedOutput(
                final_response=disclaimer_after_truncation.final_response,
                was_modified=True,
                modification_reason=f"{length_result.modification_reason}; disclaimer appended",
                flag="too_long+disclaimer",
                should_log=False
            )
        return length_result

    # Step 6 — disclaimer injection (on full, clean response)
    disclaimer_result = inject_disclaimer(response, language)
    if disclaimer_result:
        return disclaimer_result

    # All checks passed — return as-is
    return GuardedOutput(
        final_response=response,
        was_modified=False,
        should_log=False
    )


