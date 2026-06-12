# Remembers how a clinic's spreadsheet columns map to our DB fields, per import
# type — so the next upload with the same headers is pre-mapped automatically.

from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
from app.database import Base


class ImportMapping(Base):
    __tablename__ = "import_mappings"
    __table_args__ = (
        UniqueConstraint("tenant_id", "entity", name="uq_import_mapping_tenant_entity"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    entity = Column(String(30), nullable=False)  # patients | doctors | staff | services | appointments
    mapping = Column(JSONB, default=dict)        # {"their column header": "our_field", ...}
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
