# One subscription per clinic (tenant). Tracks trial, paid status, and the
# gateway's identifiers so webhooks can correlate events back to the clinic.
# The clinic's effective access is derived from status + the period/trial dates
# (see services/subscription_service.py) — never trusted from the frontend.

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.database import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, unique=True, index=True)
    plan = Column(String(20), nullable=False, default="starter")
    # trialing | active | past_due | cancelled | expired
    status = Column(String(20), nullable=False, default="trialing")
    gateway = Column(String(20))                 # manual | safepay | ...
    gateway_customer_id = Column(String(120))
    gateway_subscription_id = Column(String(120))
    checkout_ref = Column(String(120), index=True)   # correlates a pending checkout to its webhook
    pending_plan = Column(String(20))            # plan the in-flight checkout is for
    trial_ends_at = Column(DateTime(timezone=True))
    current_period_end = Column(DateTime(timezone=True))
    cancel_at_period_end = Column(Boolean, default=False, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
