# Defines the appointments table. Every time a patient books a slot through the chatbot,
# it gets saved here.
# The clinic admin sees all bookings in their dashboard from this table.

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=True, index=True)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("doctors.id"), nullable=False)
    patient_name = Column(String(255), nullable=False)
    patient_phone = Column(String(50), nullable=False)
    patient_concern = Column(Text)
    slot_datetime = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(50), default="pending")
    notes = Column(Text)
    reminder_sent = Column(Boolean, default=False, nullable=False, server_default="false")
    checked_in = Column(Boolean, default=False, nullable=False, server_default="false")
    checked_in_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index(
            "uq_active_appointment_slot",
            "tenant_id",
            "doctor_id",
            "slot_datetime",
            unique=True,
            postgresql_where=status.in_(["pending", "confirmed"]),
        ),
    )

    tenant = relationship("Tenant", back_populates="appointments")
    branch = relationship("Branch", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")
