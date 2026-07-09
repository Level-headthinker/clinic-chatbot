from typing import Optional
from sqlalchemy.orm import Session
from app.models.flagged_log import FlaggedLog
from app.models.interaction_event import InteractionEvent


def classify_outcome(*, booked: bool, lead_captured: bool,
                     slots_offered: bool) -> str:
    """Reduce a turn's results to one outcome label (most-converted wins).

    Pure function so it's trivially testable and channel-agnostic:
      booked > lead_captured > slots_offered > answered
    """
    if booked:
        return "booked"
    if lead_captured:
        return "lead_captured"
    if slots_offered:
        return "slots_offered"
    return "answered"


def log_interaction(
    db: Session,
    *,
    tenant_id,
    branch_id=None,
    session_token: Optional[str] = None,
    modality: str = "text",
    intent: Optional[str] = None,
    language: Optional[str] = None,
    outcome: str = "answered",
    is_returning: bool = False,
    visit_count: int = 0,
    kb_hit: bool = False,
    output_flagged: bool = False,
    has_contact: bool = False,
) -> None:
    """Record one turn of the data feedback loop.

    Best-effort: this must NEVER break a conversation. Stores derived signals
    only — no message text or patient PII (see InteractionEvent docstring).
    Commits standalone so the event survives even if the caller later rolls back.
    """
    try:
        db.add(InteractionEvent(
            tenant_id=tenant_id,
            branch_id=branch_id,
            session_token=session_token,
            modality=modality or "text",
            intent=intent,
            language=language,
            outcome=outcome,
            is_returning=bool(is_returning),
            visit_count=int(visit_count or 0),
            kb_hit=bool(kb_hit),
            output_flagged=bool(output_flagged),
            has_contact=bool(has_contact),
        ))
        db.commit()
    except Exception:
        # Never let analytics logging break the chat.
        try:
            db.rollback()
        except Exception:
            pass


def log_input_flag(
    db: Session,
    flag_type: str,
    flagged_message: str,
    blocked_reason: Optional[str],
    session_token: Optional[str] = None,
    tenant_id=None,
    branch_id=None,
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
            branch_id=branch_id,
            session_token=session_token,
            flag_type=flag_type,
            source="input_guard",
            flagged_message=flagged_message[:1000],
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
    branch_id=None,
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
            branch_id=branch_id,
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