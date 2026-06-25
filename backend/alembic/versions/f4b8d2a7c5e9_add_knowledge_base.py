"""add knowledge_base table

Revision ID: f4b8d2a7c5e9
Revises: e2f6a9c4b8d3
Create Date: 2026-06-25 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'f4b8d2a7c5e9'
down_revision: Union[str, Sequence[str], None] = 'e2f6a9c4b8d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'knowledge_base',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id'), nullable=False, index=True),
        sa.Column('branch_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('branches.id'), nullable=True),
        sa.Column('question', sa.String(500), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('category', sa.String(100)),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_kb_fts ON knowledge_base "
        "USING GIN (to_tsvector('english', question || ' ' || answer))"
    )


def downgrade() -> None:
    op.drop_table('knowledge_base')
