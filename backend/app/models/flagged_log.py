import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base


class FlaggedLog(Base):
    __tablename__ = "flagged_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Which clinic — nullable for pre-session blocks
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    branch_id = Column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Which chat session — nullable if blocked before session created
    session_token = Column(String(255), nullable=True, index=True)

    # Category — matches GuardResult.flag values
    # Input:  "injection", "role_override", "jailbreak", "data_extraction",
    #         "sql_injection", "prompt_extraction", "fabrication",
    #         "rate_limit", "spam", "too_long"
    # Output: "medical_advice", "patient_leak", "emergency_override"
    flag_type = Column(String(100), nullable=False, index=True)

    # Where the flag was raised
    source = Column(String(50), nullable=False)  # "input_guard" or "output_guard"

    # The message that was flagged — stored for review
    flagged_message = Column(Text, nullable=True)

    # The AI response that was intercepted (output guard only)
    intercepted_response = Column(Text, nullable=True)

    # The safe response that was returned to the user
    safe_response = Column(Text, nullable=True)

    # Human-readable reason shown to the user
    blocked_reason = Column(Text, nullable=True)

    # Whether a human has reviewed this flag
    reviewed = Column(Boolean, default=False, nullable=False)
    reviewed_note = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )