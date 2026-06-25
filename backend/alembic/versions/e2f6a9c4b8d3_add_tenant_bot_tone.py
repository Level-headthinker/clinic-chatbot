"""add bot_tone to tenants

Revision ID: e2f6a9c4b8d3
Revises: d1a8f4b6c3e2
Create Date: 2026-06-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e2f6a9c4b8d3'
down_revision: Union[str, Sequence[str], None] = 'd1a8f4b6c3e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tenants', sa.Column(
        'bot_tone', sa.String(20), nullable=True, server_default='warm'))


def downgrade() -> None:
    op.drop_column('tenants', 'bot_tone')
