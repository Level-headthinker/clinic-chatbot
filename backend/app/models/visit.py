from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, ForeignKey, Date
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base


class VisitRecord(Base):
    __tablename__ = "visit_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("doctors.id"), nullable=True)
    visit_date = Column(DateTime(timezone=True), server_default=func.now())
    complaint = Column(Text)
    diagnosis = Column(Text)
    prescription = Column(JSONB, default=list)
    tests_ordered = Column(Text)
    test_results = Column(Text)
    doctor_notes = Column(Text)
    next_visit_date = Column(Date)
    fee = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    tenant = relationship("Tenant", backref="visit_records")
    patient = relationship("Patient", back_populates="visit_records")
    doctor = relationship("Doctor", backref="visit_records")
    invoice = relationship("Invoice", back_populates="visit", uselist=False)