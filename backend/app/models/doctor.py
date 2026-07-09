# Defines the doctors table. Each clinic adds their own doctors.
# The chatbot uses this data to answer "which doctors do you have?"
# and to show available slots when booking.

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ARRAY

import uuid
from app.database import Base


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    specialty = Column(String(255), nullable=False)
    qualification = Column(String(255))
    bio = Column(Text)
    fee = Column(String(50))
    available_slots = Column(JSONB, default=list)
    treatments = Column(ARRAY(Text), default=list)
    timings = Column(JSONB, default=list)
    # How many patients this doctor can see in ONE time-slot. Default 1 preserves
    # the original one-booking-per-slot behaviour; raise it for high-throughput
    # doctors (e.g. a GP seeing 3 walk-ins per 30-min block).
    slot_capacity = Column(Integer, default=1, nullable=False, server_default="1")
    is_ready = Column(Boolean, default=False, nullable=False, server_default="false")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    tenant = relationship("Tenant", back_populates="doctors")
    branch = relationship("Branch", back_populates="doctors")
    appointments = relationship("Appointment", back_populates="doctor")