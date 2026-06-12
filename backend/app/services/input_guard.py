# ============================================================
# INPUT GUARD — Phase 1 of AI Safety Guardrails
# ============================================================
# This runs BEFORE every message reaches the LLM.
# Think of it as the front door of your system.
# It does 4 things in order:
#   1. Sanitize  — strip HTML, scripts, invisible chars
#   2. Length    — reject messages that are too long or empty
#   3. Rate limit — block sessions sending too many messages
#   4. Injection  — detect prompt injection and jailbreak attempts
#
# If any check fails, the message never reaches Groq.
# Returns a GuardResult so chat.py knows what happened and why.
# ============================================================

import re
import time
from dataclasses import dataclass, field
from collections import defaultdict
from typing import Optional


# ── Result object returned by the guard ──────────────────────
@dataclass
class GuardResult:
    allowed: bool               # True = safe to proceed
    sanitized_message: str      # Cleaned version of the input
    blocked_reason: Optional[str] = None   # Why it was blocked
    flag: Optional[str] = None  # Category: "injection", "rate_limit", etc.
    should_log: bool = False    # True = save this for admin review


# ── Configuration — change these without touching logic ──────
class GuardConfig:
    # Message length
    MAX_MESSAGE_LENGTH = 500        # chars — enough for any appointment request
    MIN_MESSAGE_LENGTH = 1          # reject truly empty messages

    # Rate limiting — per session token
    MAX_MESSAGES_PER_WINDOW = 20    # max messages allowed
    RATE_WINDOW_SECONDS = 60        # within this many seconds

    # Repeated identical message spam
    MAX_IDENTICAL_REPEATS = 3       # block if same message sent N times in a row


# ── In-memory rate limit store ───────────────────────────────
# Stores {session_token: [timestamp, timestamp, ...]}
# No Redis needed for a small system. Resets on server restart
# which is fine — Render restarts clear abuse anyway.
_rate_store: dict[str, list[float]] = defaultdict(list)
_last_message_store: dict[str, list[str]] = defaultdict(list)


def _clean_rate_store(session_token: str) -> None:
    """Remove timestamps older than the rate window."""
    now = time.time()
    cutoff = now - GuardConfig.RATE_WINDOW_SECONDS
    _rate_store[session_token] = [
        t for t in _rate_store[session_token] if t > cutoff
    ]


# ── Step 1: Sanitize ─────────────────────────────────────────
def sanitize(message: str) -> str:
    """
    Clean the message before any processing.
    Removes HTML tags, script content, invisible Unicode tricks,
    and normalizes whitespace.
    Does NOT remove Urdu script — only dangerous markup.
    """
    # Remove HTML tags like <script>, <img>, <a href=...>
    message = re.sub(r"<[^>]+>", "", message)

    # Remove javascript: protocol attempts
    message = re.sub(r"javascript\s*:", "", message, flags=re.IGNORECASE)

    # Remove null bytes and other invisible control characters
    # but keep newlines and tabs (legitimate in long messages)
    message = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", message)

    # Remove Unicode direction override characters (used to hide text)
    # U+202A–U+202E, U+2066–U+2069
    message = re.sub(r"[\u202a-\u202e\u2066-\u2069]", "", message)

    # Collapse multiple spaces/newlines into one
    message = re.sub(r"\s+", " ", message).strip()

    return message


# ── Step 2: Length check ─────────────────────────────────────
def check_length(message: str) -> Optional[GuardResult]:
    """
    Returns a blocked GuardResult if message is too short or too long.
    Returns None if length is acceptable.
    """
    if len(message) < GuardConfig.MIN_MESSAGE_LENGTH:
        return GuardResult(
            allowed=False,
            sanitized_message=message,
            blocked_reason="Message is empty.",
            flag="empty",
            should_log=False
        )

    if len(message) > GuardConfig.MAX_MESSAGE_LENGTH:
        return GuardResult(
            allowed=False,
            sanitized_message=message,
            blocked_reason=(
                f"Message too long. Please keep it under "
                f"{GuardConfig.MAX_MESSAGE_LENGTH} characters."
            ),
            flag="too_long",
            should_log=True  # Log long messages — could be injection attempts
        )

    return None


# ── Step 3: Rate limit ───────────────────────────────────────
def check_rate_limit(session_token: str, message: str) -> Optional[GuardResult]:
    """
    Blocks sessions that send too many messages too quickly,
    or repeat the same message too many times (bot/spam detection).
    Returns None if within limits.
    """
    _clean_rate_store(session_token)

    # Check message frequency
    count = len(_rate_store[session_token])
    if count >= GuardConfig.MAX_MESSAGES_PER_WINDOW:
        return GuardResult(
            allowed=False,
            sanitized_message=message,
            blocked_reason=(
                "Too many messages. Please wait a moment before sending again."
            ),
            flag="rate_limit",
            should_log=True
        )

    # Check identical message spam
    recent = _last_message_store[session_token]
    recent.append(message.lower().strip())
    _last_message_store[session_token] = recent[-10:]  # keep last 10 only

    repeat_count = sum(
        1 for m in recent[-GuardConfig.MAX_IDENTICAL_REPEATS:]
        if m == message.lower().strip()
    )
    if repeat_count >= GuardConfig.MAX_IDENTICAL_REPEATS:
        return GuardResult(
            allowed=False,
            sanitized_message=message,
            blocked_reason="Please avoid sending the same message repeatedly.",
            flag="spam",
            should_log=True
        )

    # All clear — record this message timestamp
    _rate_store[session_token].append(time.time())
    return None


# ── Step 4: Injection detection ──────────────────────────────
#
# These patterns cover:
#   - Classic English jailbreaks
#   - Roman Urdu equivalents
#   - Data extraction attempts
#   - Role override attempts
#
# Design principle: we match on INTENT not exact wording.
# Each pattern has a comment explaining what attack it catches.

INJECTION_PATTERNS = [
    # ── Known jailbreak names/techniques ──
    # Checked FIRST: "You are now DAN" must classify as the more specific
    # "jailbreak", not the generic role_override that would also match it.
    (r"\bDAN\b", "jailbreak"),                             # Do Anything Now
    (r"jailbreak", "jailbreak"),
    (r"developer\s+mode", "jailbreak"),
    (r"unrestricted\s+mode", "jailbreak"),
    (r"no\s+restrictions", "jailbreak"),
    (r"without\s+(any\s+)?limitations", "jailbreak"),

    # ── Role override attempts ──
    (r"ignore\s+(your\s+)?(previous\s+|all\s+)?instructions", "role_override"),
    (r"forget\s+(your\s+)?(previous\s+|all\s+)?instructions", "role_override"),
    (r"you\s+are\s+now\s+\w+", "role_override"),          # "you are now a pirate"
    (r"act\s+as\s+(if\s+you\s+are|a\s+)", "role_override"),
    (r"pretend\s+(you\s+are|to\s+be)", "role_override"),
    (r"your\s+new\s+(role|instructions|task|job)\s+is", "role_override"),
    (r"from\s+now\s+on\s+(you\s+are|act)", "role_override"),
    (r"disregard\s+(all\s+)?(previous|your)", "role_override"),

    # ── System prompt extraction ──
    (r"(show|reveal|print|output|tell me|what is)\s+(me\s+)?(your\s+)?(system\s+prompt|instructions)", "prompt_extraction"),
    (r"repeat\s+(your\s+)?(system|initial|original)\s+(prompt|instructions)", "prompt_extraction"),
    (r"what\s+(were\s+)?you\s+(told|instructed|programmed)", "prompt_extraction"),

    # ── Data extraction attempts ──
    (r"(list|show|give me|tell me)\s+(me\s+)?(all\s+)?(patients|users|appointments|records|database)", "data_extraction"),
    (r"(how many|count)\s+(patients|users|records)", "data_extraction"),
    (r"(dump|export|extract)\s+(the\s+)?(database|data|records|table)", "data_extraction"),
    (r"select\s+\*\s+from", "sql_injection"),              # SQL injection attempt
    (r"(drop|delete|truncate)\s+table", "sql_injection"),

    # ── Roman Urdu injection attempts ──
    (r"apni\s+(instructions|hid[ae]yat)\s+bhool\s+ja", "role_override"),
    (r"naye\s+(instructions|hid[ae]yat)\s+follow\s+kar", "role_override"),
    (r"tum\s+ab\s+\w+\s+ho", "role_override"),            # "tum ab X ho" = "you are now X"
    (r"pehli\s+(instructions|baat)\s+bhool", "role_override"),

    # ── Asking bot to lie or fabricate ──
    (r"(make up|invent|fabricate|hallucinate)\s+(a\s+)?(doctor|slot|appointment)", "fabrication"),
    (r"(pretend|act\s+as\s+if)\s+(there\s+is|you\s+have)\s+(a\s+)?doctor", "fabrication"),
]

# Compile all patterns once at import time for performance
_COMPILED_PATTERNS = [
    (re.compile(pattern, re.IGNORECASE), flag)
    for pattern, flag in INJECTION_PATTERNS
]


def check_injection(message: str) -> Optional[GuardResult]:
    """
    Scans message for injection patterns.
    Returns a blocked GuardResult on first match, None if clean.
    """
    for pattern, flag in _COMPILED_PATTERNS:
        if pattern.search(message):
            return GuardResult(
                allowed=False,
                sanitized_message=message,
                blocked_reason=(
                    "I can only help with clinic appointments and information. "
                    "I cannot process that kind of request."
                ),
                flag=flag,
                should_log=True   # Always log injection attempts for admin review
            )
    return None


# ── Main entry point ─────────────────────────────────────────
def run_input_guard(message: str, session_token: str) -> GuardResult:
    """
    Run all input checks in order. Call this in chat.py before
    passing anything to the LLM.

    Order matters:
      Sanitize first (so injection checks run on clean text),
      then length (cheap check before expensive ones),
      then rate limit (per-session state check),
      then injection (regex scan).

    Usage in chat.py:
        result = run_input_guard(data.message, session_token)
        if not result.allowed:
            return blocked_response(result)
        # use result.sanitized_message going forward
    """
    # Step 1 — always sanitize first
    clean = sanitize(message)

    # Step 2 — length check on sanitized text
    length_result = check_length(clean)
    if length_result:
        return length_result

    # Step 3 — rate limit check
    rate_result = check_rate_limit(session_token, clean)
    if rate_result:
        return rate_result

    # Step 4 — injection detection
    injection_result = check_injection(clean)
    if injection_result:
        return injection_result

    # All checks passed
    return GuardResult(
        allowed=True,
        sanitized_message=clean,
        should_log=False
    )
