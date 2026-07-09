import uuid
from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base


class InteractionEvent(Base):
    """One row per conversational turn — the raw signal for the data feedback loop.

    Append-only. This is what powers "conversion rate", "top intents", "handoff /
    failure clusters" without re-reading every chat transcript.

    PRIVACY BY DESIGN: this table stores ONLY derived signals — no message text,
    no patient name/phone, nothing that identifies a person. It's healthcare
    data's feedback loop, so it must be safe to aggregate freely (and, later,
    to learn from globally across tenants) without ever exposing PHI.
    """
    __tablename__ = "interaction_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Which clinic / branch produced this turn (isolation + per-tenant analytics).
    tenant_id = Column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    branch_id = Column(
        UUID(as_uuid=True), ForeignKey("branches.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    # Groups turns of the same conversation (NOT the patient — the session token).
    session_token = Column(String(255), nullable=True, index=True)

    # Channel: "text" (web/WhatsApp text) or "voice" (voice note / call).
    modality = Column(String(20), nullable=False, default="text")

    # What the turn was about — extract_intent(): "book_appointment", "general", …
    intent = Column(String(50), nullable=True, index=True)
    language = Column(String(20), nullable=True)

    # The turn's result — the conversion signal:
    #   booked | lead_captured | slots_offered | answered
    outcome = Column(String(30), nullable=False, index=True)

    # Context flags — cheap booleans that make failure/quality clusters findable.
    is_returning = Column(Boolean, default=False, nullable=False)
    visit_count = Column(Integer, default=0, nullable=False)
    kb_hit = Column(Boolean, default=False, nullable=False)          # KB had an answer
    output_flagged = Column(Boolean, default=False, nullable=False)  # output guard fired
    has_contact = Column(Boolean, default=False, nullable=False)     # name + phone known

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), index=True,
    )
