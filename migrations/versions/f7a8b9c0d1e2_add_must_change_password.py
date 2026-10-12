"""add must_change_password flag to users

Revision ID: f7a8b9c0d1e2
Revises: e5f6a7b8c9d0
Create Date: 2026-10-12 08:00:00.000000

Accounts created with a system-assigned bootstrap password (e.g. national ID)
must rotate it on first login. Existing rows default to False (no forced
rotation for accounts created before this flag existed).
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f7a8b9c0d1e2"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("must_change_password", sa.Boolean(), nullable=True))
    op.execute(
        "UPDATE users SET must_change_password = FALSE "
        "WHERE must_change_password IS NULL"
    )
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("must_change_password", nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("must_change_password")
