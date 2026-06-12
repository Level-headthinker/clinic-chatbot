# Maps a Meta WhatsApp phone_number_id to the clinic (tenant/branch) that owns it.
# One Meta App, one webhook URL, many clinic numbers — the webhook router looks up
# this table to decide which clinic's brain answers an incoming message.
# Also tracks per-clinic monthly message usage against a configurable limit.

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.database import Base


class WhatsAppNumberMapping(Base):
    __tablename__ = "whatsapp_number_mappings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=True)
    phone_number_id = Column(String(64), unique=True, nullable=False, index=True)  # Meta's ID
    whatsapp_number = Column(String(32))  # human-readable, e.g. +923001234567
    is_active = Column(Boolean, default=True, nullable=False)
    message_limit_monthly = Column(Integer, default=1000, nullable=False)
    messages_used_this_month = Column(Integer, default=0, nullable=False)
    limit_reset_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
