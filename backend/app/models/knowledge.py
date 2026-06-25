# Clinic knowledge base — Q&A / info entries the bot retrieves at answer time
# (lightweight RAG via Postgres full-text search). Tenant-scoped: each clinic's
# knowledge is isolated, exactly like every other model.

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.database import Base


class KnowledgeEntry(Base):
    __tablename__ = "knowledge_base"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=True)
    question = Column(String(500), nullable=False)   # the topic / question
    answer = Column(Text, nullable=False)            # the answer the bot should use
    category = Column(String(100))                   # optional grouping (e.g. "Pricing", "Pre-care")
    is_active = Column(Boolean, default=True, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
