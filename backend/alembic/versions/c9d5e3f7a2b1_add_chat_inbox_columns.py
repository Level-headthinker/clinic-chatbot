"""add human_handling + unread_count to chat_sessions

Revision ID: c9d5e3f7a2b1
Revises: b8c4d2e6f1a9
Create Date: 2026-06-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c9d5e3f7a2b1'
down_revision: Union[str, Sequence[str], None] = 'b8c4d2e6f1a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('chat_sessions', sa.Column(
        'human_handling', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('chat_sessions', sa.Column(
        'unread_count', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('chat_sessions', 'unread_count')
    op.drop_column('chat_sessions', 'human_handling')
