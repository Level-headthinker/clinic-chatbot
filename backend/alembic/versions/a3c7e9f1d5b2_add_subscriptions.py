"""add subscriptions table

Revision ID: a3c7e9f1d5b2
Revises: f4b8d2a7c5e9
Create Date: 2026-06-25 02:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'a3c7e9f1d5b2'
down_revision: Union[str, Sequence[str], None] = 'f4b8d2a7c5e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id'), nullable=False, unique=True, index=True),
        sa.Column('plan', sa.String(20), nullable=False, server_default='starter'),
        sa.Column('status', sa.String(20), nullable=False, server_default='trialing'),
        sa.Column('gateway', sa.String(20)),
        sa.Column('gateway_customer_id', sa.String(120)),
        sa.Column('gateway_subscription_id', sa.String(120)),
        sa.Column('checkout_ref', sa.String(120), index=True),
        sa.Column('pending_plan', sa.String(20)),
        sa.Column('trial_ends_at', sa.DateTime(timezone=True)),
        sa.Column('current_period_end', sa.DateTime(timezone=True)),
        sa.Column('cancel_at_period_end', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    op.drop_table('subscriptions')
