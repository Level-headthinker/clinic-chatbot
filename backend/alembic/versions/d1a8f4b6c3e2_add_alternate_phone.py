"""add alternate_phone to appointments, leads, chat_sessions

Revision ID: d1a8f4b6c3e2
Revises: c9d5e3f7a2b1
Create Date: 2026-06-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd1a8f4b6c3e2'
down_revision: Union[str, Sequence[str], None] = 'c9d5e3f7a2b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('appointments', sa.Column('alternate_phone', sa.String(50), nullable=True))
    op.add_column('leads', sa.Column('alternate_phone', sa.String(50), nullable=True))
    op.add_column('chat_sessions', sa.Column('alternate_phone', sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column('chat_sessions', 'alternate_phone')
    op.drop_column('leads', 'alternate_phone')
    op.drop_column('appointments', 'alternate_phone')
