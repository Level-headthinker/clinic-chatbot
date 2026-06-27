from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base


class FollowUp(Base):
    __tablename__ = "follow_ups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=True, index=True)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=True, index=True)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True, index=True)
    # The visit a next-visit reminder was generated from (dedup + traceability).
    visit_id = Column(UUID(as_uuid=True), ForeignKey("visit_records.id"), nullable=True, index=True)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    title = Column(String(255), nullable=False)
    notes = Column(Text, nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=False)
    # pending | done | cancelled
    status = Column(String(50), default="pending", nullable=False)
    # How this follow-up was created: manual | next_visit | lead_nudge
    kind = Column(String(20), nullable=False, server_default="manual")
    channel = Column(String(20))                          # whatsapp, when an auto reminder was sent
    reminder_sent_at = Column(DateTime(timezone=True))    # when the auto message actually went out
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    patient = relationship("Patient", foreign_keys=[patient_id])
    lead = relationship("Lead", foreign_keys=[lead_id])
