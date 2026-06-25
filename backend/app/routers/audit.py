# Read-only view of the clinic's audit trail. Tenant-scoped: an admin only ever
# sees their own clinic's history. The trail itself is written by
# app.services.audit.log_audit from the endpoints that change data.
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.services.auth import require_admin_user

router = APIRouter(prefix="/audit-logs", tags=["Audit"])


@router.get("/")
def list_audit_logs(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    q = db.query(AuditLog).filter(AuditLog.tenant_id == current_user.tenant_id)
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if entity_id:
        q = q.filter(AuditLog.entity_id == str(entity_id))
    if action:
        q = q.filter(AuditLog.action == action)

    total = q.count()
    rows = q.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "items": [
            {
                "id": str(r.id),
                "action": r.action,
                "entity_type": r.entity_type,
                "entity_id": r.entity_id,
                "summary": r.summary,
                "before": r.before,
                "after": r.after,
                "user_email": r.user_email,
                "ip": r.ip,
                "created_at": str(r.created_at) if r.created_at else None,
            }
            for r in rows
        ],
    }
