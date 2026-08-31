"""add online link columns to classes and sessions

Revision ID: e5f6a7b8c9d0
Revises: b3c4d5e6f7a9
Create Date: 2026-09-01 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("academy_classes") as batch_op:
        batch_op.add_column(sa.Column("online_link", sa.String(500), nullable=True))

    with op.batch_alter_table("sessions") as batch_op:
        batch_op.add_column(sa.Column("online_link", sa.String(500), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("sessions") as batch_op:
        batch_op.drop_column("online_link")

    with op.batch_alter_table("academy_classes") as batch_op:
        batch_op.drop_column("online_link")
