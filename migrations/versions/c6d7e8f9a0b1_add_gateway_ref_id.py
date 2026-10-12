"""add gateway_ref_id to financial transactions

Revision ID: c6d7e8f9a0b1
Revises: b5c6d7e8f9a0
Create Date: 2026-10-12 09:00:00.000000

Stores the provider-issued payment identifier separately so the lookup
authority in reference_number is never overwritten by callback handling.
Purely additive nullable column.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c6d7e8f9a0b1"
down_revision = "b5c6d7e8f9a0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("financial_transactions") as batch_op:
        batch_op.add_column(sa.Column("gateway_ref_id", sa.String(100), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("financial_transactions") as batch_op:
        batch_op.drop_column("gateway_ref_id")
