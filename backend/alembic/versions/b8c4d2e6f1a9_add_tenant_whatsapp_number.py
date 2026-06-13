"""add whatsapp_number to tenants

Revision ID: b8c4d2e6f1a9
Revises: a7b3c9d1e2f4
Create Date: 2026-06-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b8c4d2e6f1a9'
down_revision: Union[str, Sequence[str], None] = 'a7b3c9d1e2f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tenants', sa.Column('whatsapp_number', sa.String(32), nullable=True))


def downgrade() -> None:
    op.drop_column('tenants', 'whatsapp_number')
