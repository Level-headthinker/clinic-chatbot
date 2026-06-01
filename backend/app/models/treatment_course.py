from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base


class TreatmentCourse(Base):
    __tablename__ = "treatment_courses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=True)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    patient_phone = Column(String(50))
    service_name = Column(String(255), nullable=False)
    total_sessions = Column(Integer, nullable=False)
    completed_sessions = Column(Integer, default=0)
    price_per_course = Column(Numeric(10, 2))
    status = Column(String(20), default="active")  # active, completed, cancelled
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    patient = relationship("Patient", backref="treatment_courses")
