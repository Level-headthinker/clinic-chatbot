from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("tenant_id", "invoice_number", name="uq_invoice_number_tenant"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    visit_id = Column(UUID(as_uuid=True), ForeignKey("visit_records.id"), nullable=True)
    invoice_number = Column(String(50), nullable=False)
    consultation_fee = Column(Integer, default=0)
    additional_charges = Column(JSONB, default=list)
    total_amount = Column(Integer, default=0)
    paid_amount = Column(Integer, default=0)
    payment_status = Column(String(50), default="unpaid")
    payment_method = Column(String(50))
    notes = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    tenant = relationship("Tenant", backref="invoices")
    patient = relationship("Patient", back_populates="invoices")
    visit = relationship("VisitRecord", back_populates="invoice")
