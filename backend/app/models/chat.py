# Two tables in one file — chat_sessions and leads.
# Chat sessions store the full conversation history.
# Leads store patient contact info collected during chat.
# These are the two most important tables for the chatbot.

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=True, index=True)
    session_token = Column(String(255), unique=True, nullable=False)
    messages = Column(JSONB, default=list)
    language = Column(String(10), default="en")
    patient_name = Column(String(255))
    patient_phone = Column(String(50))
    current_intent = Column(String(100))
    # Team-inbox / human takeover: when a staff member takes over a conversation,
    # the bot stays quiet and the receptionist replies by hand from the dashboard.
    human_handling = Column(Boolean, default=False, nullable=False, server_default="false")
    unread_count = Column(Integer, default=0, nullable=False, server_default="0")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    tenant = relationship("Tenant", back_populates="chat_sessions")
    branch = relationship("Branch", back_populates="chat_sessions")


class Lead(Base):
    __tablename__ = "leads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=False)
    concern = Column(Text)
    source = Column(String(100), default="chatbot")
    status = Column(String(50), default="new")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Text, nullable=True)

    tenant = relationship("Tenant", back_populates="leads")
    branch = relationship("Branch", back_populates="leads")