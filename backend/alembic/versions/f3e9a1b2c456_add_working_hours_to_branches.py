"""add_working_hours_to_branches

Revision ID: f3e9a1b2c456
Revises: 0122a077aa2f
Create Date: 2026-05-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f3e9a1b2c456'
down_revision: Union[str, Sequence[str], None] = '0122a077aa2f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('branches', sa.Column('working_hours', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('branches', 'working_hours')
