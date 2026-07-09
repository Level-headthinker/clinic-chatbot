import uuid
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base


class SlotOffer(Base):
    """A "a spot opened earlier — want it?" offer to a patient already booked for
    a later day. Created when someone cancels/reschedules and frees a slot today.

    Flow: patient A cancels today's 3pm → we offer that freed slot to patient B
    (booked for the same time on a later day). If B replies YES first, B's existing
    appointment is moved earlier into the freed slot and all sibling offers for
    that slot expire, so a freed seat is only ever handed out once.
    """
    __tablename__ = "slot_offers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
                       nullable=False, index=True)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id", ondelete="SET NULL"),
                       nullable=True)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("doctors.id", ondelete="CASCADE"),
                       nullable=False)
    # The patient being offered the earlier slot + the existing appointment we'd
    # move if they accept.
    patient_phone = Column(String(50), nullable=False, index=True)
    appointment_id = Column(UUID(as_uuid=True), ForeignKey("appointments.id", ondelete="CASCADE"),
                            nullable=False)
    # The freed slot being offered.
    offered_slot = Column(DateTime(timezone=True), nullable=False)

    # pending | accepted | declined | expired | filled (someone else took it)
    status = Column(String(20), nullable=False, default="pending", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
