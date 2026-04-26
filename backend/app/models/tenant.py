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
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    users = relationship("User", back_populates="tenant")
    doctors = relationship("Doctor", back_populates="tenant")
    appointments = relationship("Appointment", back_populates="tenant")
    leads = relationship("Lead", back_populates="tenant")
    chat_sessions = relationship("ChatSession", back_populates="tenant")