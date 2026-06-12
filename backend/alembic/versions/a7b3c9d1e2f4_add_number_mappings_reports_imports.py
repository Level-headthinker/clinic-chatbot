"""add whatsapp_number_mappings, system_reports, import_mappings

Revision ID: a7b3c9d1e2f4
Revises: f3e9a1b2c456
Create Date: 2026-06-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'a7b3c9d1e2f4'
down_revision: Union[str, Sequence[str], None] = 'f3e9a1b2c456'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'whatsapp_number_mappings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id'), nullable=False, index=True),
        sa.Column('branch_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('branches.id'), nullable=True),
        sa.Column('phone_number_id', sa.String(64), nullable=False, unique=True, index=True),
        sa.Column('whatsapp_number', sa.String(32)),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('message_limit_monthly', sa.Integer(), nullable=False, server_default='1000'),
        sa.Column('messages_used_this_month', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('limit_reset_date', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        'system_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('clinic_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id'), nullable=True, index=True),
        sa.Column('report_type', sa.String(20), nullable=False),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('metrics', postgresql.JSONB(), server_default='{}'),
        sa.Column('xlsx_path', sa.String(500)),
        sa.Column('pdf_path', sa.String(500)),
    )
    op.create_table(
        'import_mappings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id'), nullable=False, index=True),
        sa.Column('entity', sa.String(30), nullable=False),
        sa.Column('mapping', postgresql.JSONB(), server_default='{}'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('tenant_id', 'entity', name='uq_import_mapping_tenant_entity'),
    )


def downgrade() -> None:
    op.drop_table('import_mappings')
    op.drop_table('system_reports')
    op.drop_table('whatsapp_number_mappings')
