"""enforce one payroll payment per teacher and period

Revision ID: d7e8f9a0b1c2
Revises: c6d7e8f9a0b1
Create Date: 2026-10-12 09:30:00.000000

Adds a unique constraint so concurrent finalizations cannot create
duplicate TeacherPayment rows for the same teacher and period. The
service keeps its pre-check for a friendly error and converts the
constraint violation into PayrollError. Verified duplicate-free on
production before applying (teacher_payments is empty there).
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d7e8f9a0b1c2"
down_revision = "c6d7e8f9a0b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("teacher_payments") as batch_op:
        batch_op.create_unique_constraint(
            "uq_teacher_payment_period",
            ["teacher_user_id", "period_start", "period_end"],
        )


def downgrade() -> None:
    with op.batch_alter_table("teacher_payments") as batch_op:
        batch_op.drop_constraint("uq_teacher_payment_period", type_="unique")
