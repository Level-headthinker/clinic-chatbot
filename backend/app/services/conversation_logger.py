from typing import Optional
from sqlalchemy.orm import Session
from app.models.flagged_log import FlaggedLog


def log_input_flag(
    db: Session,
    flag_type: str,
    flagged_message: str,
    blocked_reason: Optional[str],
    session_token: Optional[str] = None,
    tenant_id=None,
) -> None:
    """
    Log a message blocked by the InputGuard.
    Call this after run_input_guard() returns allowed=False with should_log=True.

    Args:
        db:               SQLAlchemy session — pass the request's db
        flag_type:        guard result flag e.g. "injection", "rate_limit"
        flagged_message:  the sanitized message that was blocked
        blocked_reason:   the user-facing reason string
        session_token:    chat session token (may be None if pre-session)
        tenant_id:        clinic UUID (may be None if pre-session)
    """
    try:
        entry = FlaggedLog(
            tenant_id=tenant_id,
            session_token=session_token,
            flag_type=flag_type,
            source="input_guard",
            flagged_message=flagged_message[:1000],  # cap storage
            blocked_reason=blocked_reason,
        )
        db.add(entry)
        db.commit()
    except Exception:
        # Never let logging break the chat — silently swallow
        try:
            db.rollback()
        except Exception:
            pass


def log_output_flag(
    db: Session,
    flag_type: str,
    flagged_message: str,
    intercepted_response: str,
    safe_response: str,
    session_token: Optional[str] = None,
    tenant_id=None,
) -> None:
    """
    Log a response intercepted by the OutputGuard.
    Call this when run_output_guard() changes the AI's response.

    Args:
        db:                   SQLAlchemy session
        flag_type:            "medical_advice", "patient_leak", "emergency_override"
        flagged_message:      the user message that triggered the bad response
        intercepted_response: what the AI tried to say
        safe_response:        what was actually sent to the user
        session_token:        chat session token
        tenant_id:            clinic UUID
    """
    try:
        entry = FlaggedLog(
            tenant_id=tenant_id,
            session_token=session_token,
            flag_type=flag_type,
            source="output_guard",
            flagged_message=flagged_message[:1000],
            intercepted_response=intercepted_response[:2000],
            safe_response=safe_response[:1000],
        )
        db.add(entry)
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass


def flag_type_label(flag_type: str) -> str:
    """Human-readable label for flag types — used in admin UI."""
    labels = {
        "injection":          "🔴 Prompt Injection",
        "role_override":      "🔴 Role Override Attempt",
        "jailbreak":          "🔴 Jailbreak Attempt",
        "data_extraction":    "🔴 Data Extraction Attempt",
        "sql_injection":      "🔴 SQL Injection",
        "prompt_extraction":  "🟠 System Prompt Extraction",
        "fabrication":        "🟠 Fabrication Request",
        "rate_limit":         "🟡 Rate Limit Hit",
        "spam":               "🟡 Repeated Spam",
        "too_long":           "🟡 Message Too Long",
        "medical_advice":     "🟠 Medical Advice Intercepted",
        "patient_leak":       "🔴 Patient Data Leak Intercepted",
        "emergency_override": "🔵 Emergency Booking Override",
    }
    return labels.get(flag_type, f"⚪ {flag_type}")