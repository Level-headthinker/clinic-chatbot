# Stored performance/business reports. clinic_id NULL = platform-wide report
# (superadmin); clinic_id set = that clinic's report. Generated on demand from
# the dashboard or by the weekly/monthly cron, with export files cached on disk
# so a clinic can re-download without regenerating.

from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
from app.database import Base


class SystemReport(Base):
    __tablename__ = "system_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinic_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True)
    report_type = Column(String(20), nullable=False)  # daily | weekly | monthly | yearly
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    metrics = Column(JSONB, default=dict)       # full metric payload (see services/reports.py)
    xlsx_path = Column(String(500))             # cached export files for re-download
    pdf_path = Column(String(500))
