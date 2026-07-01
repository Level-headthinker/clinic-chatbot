# Defines the tenants table in your database.
#Every business (clinic) that uses your platform is a tenant.
#All their data — doctors, appointments, leads — is linked to their tenant ID.
#This is what makes it multi-tenant.

from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    plan = Column(String(50), default="starter")
    bot_name = Column(String(100), default="ClinicBot")
    welcome_message = Column(Text, default="Hello! How can I help you today?")
    primary_color = Column(String(7), default="#2563eb")
    # Conversational tone the bot uses for this clinic (warm/formal/casual/...).
    # Injected into the LLM prompt so each clinic can pick the "feel" of its bot.
    bot_tone = Column(String(20), default="warm")
    # The clinic's own WhatsApp number (human-readable, e.g. +923001234567),
    # captured at sign-up. Routing still uses the Meta phone_number_id on the
    # whatsapp_number_mappings row — this is for display + the connect screen.
    whatsapp_number = Column(String(32))
    # Set when the clinic finishes or dismisses the getting-started wizard, so it
    # stops showing. Step completion itself is derived live from the data.
    onboarding_dismissed = Column(Boolean, default=False, nullable=False, server_default="false")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    users = relationship("User", back_populates="tenant")
    branches = relationship("Branch", back_populates="tenant")
    doctors = relationship("Doctor", back_populates="tenant")
    appointments = relationship("Appointment", back_populates="tenant")
    leads = relationship("Lead", back_populates="tenant")
    chat_sessions = relationship("ChatSession", back_populates="tenant")