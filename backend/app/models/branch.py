from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base


class Branch(Base):
    __tablename__ = "branches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    phone = Column(String(50), nullable=True)
    timezone = Column(String(50), default="Asia/Karachi")

    # Branch-level chatbot overrides (fall back to tenant settings if null)
    bot_name = Column(String(100), nullable=True)
    welcome_message = Column(Text, nullable=True)

    is_main_branch = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    tenant = relationship("Tenant", back_populates="branches")
    users = relationship("User", back_populates="branch")
    doctors = relationship("Doctor", back_populates="branch")
    appointments = relationship("Appointment", back_populates="branch")
    leads = relationship("Lead", back_populates="branch")
    chat_sessions = relationship("ChatSession", back_populates="branch")
