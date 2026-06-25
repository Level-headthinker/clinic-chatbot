# Append-only audit trail. Records who did what to which record, and when.
#
# Why: this is healthcare data. When a patient/appointment/invoice is changed
# or deleted, we need to know who did it and be able to reconstruct what was
# lost. Rows are NEVER updated or deleted — the table only grows. Combined with
# soft-deletes, this means an accidental change is always traceable and the old
# values are recoverable from `before` without restoring a whole backup.

from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    # Who — nullable so system/automated actions can be recorded too.
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    user_email = Column(String(255))            # denormalised so the trail survives user deletion
    action = Column(String(20), nullable=False)  # create | update | delete | restore | export
    entity_type = Column(String(50), nullable=False)   # patient | appointment | invoice | ...
    entity_id = Column(String(64))               # the affected row's id (string — works for any pk)
    summary = Column(String(255))                # human-readable, e.g. "Deleted patient Ali Khan"
    before = Column(JSONB)                        # snapshot of changed fields BEFORE the change
    after = Column(JSONB)                         # snapshot AFTER (for updates/creates)
    ip = Column(String(64))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    __table_args__ = (
        Index("ix_audit_tenant_created", "tenant_id", "created_at"),
        Index("ix_audit_entity", "entity_type", "entity_id"),
    )
