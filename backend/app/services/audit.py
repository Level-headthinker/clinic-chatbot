# Helper for writing audit-trail entries. Import and call `log_audit(...)`
# from any endpoint that creates, changes, deletes, restores, or exports data.
#
# Design notes:
#   - Best-effort: auditing must NEVER break the underlying business action.
#     If a log write fails we swallow the error (and report to Sentry) rather
#     than 500 the user's request.
#   - The caller is responsible for committing. We add() to the same session so
#     the audit row commits atomically with the change it describes.
from __future__ import annotations

from typing import Any, Optional
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


# Fields we must never copy into an audit snapshot.
_REDACT = {"hashed_password", "password", "token", "access_token", "secret"}


def _clean(data: Optional[dict]) -> Optional[dict]:
    if not data:
        return data
    out = {}
    for k, v in data.items():
        if k in _REDACT:
            continue
        # JSONB needs serialisable values — stringify anything exotic.
        if isinstance(v, (str, int, float, bool)) or v is None:
            out[k] = v
        else:
            out[k] = str(v)
    return out


def log_audit(
    db: Session,
    *,
    tenant_id,
    action: str,
    entity_type: str,
    entity_id: Any = None,
    summary: str = "",
    before: Optional[dict] = None,
    after: Optional[dict] = None,
    user=None,
    request=None,
    commit: bool = False,
) -> None:
    """Record one audit entry on the given session.

    By default does NOT commit — it rides along with the caller's commit so the
    log and the change are written together. Pass commit=True for standalone use.
    """
    try:
        ip = None
        if request is not None and getattr(request, "client", None):
            ip = request.client.host
        entry = AuditLog(
            tenant_id=tenant_id,
            user_id=getattr(user, "id", None),
            user_email=getattr(user, "email", None),
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            summary=summary[:255] if summary else None,
            before=_clean(before),
            after=_clean(after),
            ip=ip,
        )
        db.add(entry)
        if commit:
            db.commit()
    except Exception as e:  # never let auditing break the real action
        # A dropped audit row means a change happened with no trail — report it
        # (logs + Sentry) instead of swallowing it entirely.
        from app.observability import report_error
        report_error("Audit log write failed", e,
                     action=action, entity_type=entity_type)


def snapshot(obj, fields: list[str]) -> dict:
    """Pull a plain dict of the named fields off a SQLAlchemy model instance."""
    return {f: getattr(obj, f, None) for f in fields}
