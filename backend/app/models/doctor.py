# Defines the doctors table. Each clinic adds their own doctors.
# The chatbot uses this data to answer "which doctors do you have?"
# and to show available slots when booking.

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    name = Column(String(255), nullable=False)
    specialty = Column(String(255), nullable=False)
    qualification = Column(String(255))
    bio = Column(Text)
    fee = Column(String(50))
    available_slots = Column(JSONB, default=list)
    treatments = Column(JSONB, default=list)
    timings = Column(JSONB, default=list)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    tenant = relationship("Tenant", back_populates="doctors")
    appointments = relationship("Appointment", back_populates="doctor")