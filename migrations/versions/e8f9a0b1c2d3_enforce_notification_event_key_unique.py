"""enforce unique notification event keys

Revision ID: e8f9a0b1c2d3
Revises: d7e8f9a0b1c2
Create Date: 2026-10-12 10:00:00.000000

Backs event_key deduplication in create_notification: retries and repeated
runs return the existing row instead of inserting duplicates, and racing
inserts fail loudly on the constraint instead of doubling rows. NULL keys
are unaffected on PostgreSQL and SQLite. Verified safe: the production
notifications table is empty.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e8f9a0b1c2d3"
down_revision = "d7e8f9a0b1c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("notifications") as batch_op:
        batch_op.drop_index("ix_notification_event_key")
        batch_op.create_unique_constraint(
            "uq_notification_event_key", ["event_key"]
        )


def downgrade() -> None:
    with op.batch_alter_table("notifications") as batch_op:
        batch_op.drop_constraint("uq_notification_event_key", type_="unique")
        batch_op.create_index("ix_notification_event_key", ["event_key"])
