"""scope payroll uniqueness to live rows (allow void-and-refinalize)

Revision ID: f9a0b1c2d3e4
Revises: e8f9a0b1c2d3
Create Date: 2026-10-13 12:00:00.000000

Replaces the full unique constraint on
(teacher_user_id, period_start, period_end) with a partial unique index
that ignores VOIDED rows, so a voided payroll can be correctly
re-finalized while concurrent duplicate finalization stays impossible.

SQLAlchemy UniqueConstraint cannot express partial indexes portably, so
the model intentionally carries no UniqueConstraint here: the service
pre-check enforces the rule on every backend, and this partial index is
the race backstop on PostgreSQL (verified duplicate-free on production
before applying: teacher_payments is empty there).

Downgrade restores the full constraint and FAILS loudly if VOIDED
duplicates exist — it deletes nothing; resolve manually. Production
recovery is forward-only.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f9a0b1c2d3e4"
down_revision = "e8f9a0b1c2d3"
branch_labels = None
depends_on = None

_PARTIAL_WHERE = "status <> 'VOIDED'"


def upgrade() -> None:
    bind = op.get_bind()
    with op.batch_alter_table("teacher_payments") as batch_op:
        batch_op.drop_constraint("uq_teacher_payment_period", type_="unique")
    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                "CREATE UNIQUE INDEX uq_teacher_payment_period "
                "ON teacher_payments (teacher_user_id, period_start, period_end) "
                f"WHERE {_PARTIAL_WHERE}"
            )
        )
    else:
        # Non-PostgreSQL backends (migrations effectively run on PostgreSQL
        # only; kept for completeness): plain unique constraint.
        with op.batch_alter_table("teacher_payments") as batch_op:
            batch_op.create_unique_constraint(
                "uq_teacher_payment_period",
                ["teacher_user_id", "period_start", "period_end"],
            )


def downgrade() -> None:
    # NOTE: restores the FULL constraint and fails loudly if VOIDED
    # duplicates exist — it deletes nothing. Prefer forward recovery.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(sa.text("DROP INDEX IF EXISTS uq_teacher_payment_period"))
    else:
        with op.batch_alter_table("teacher_payments") as batch_op:
            batch_op.drop_constraint("uq_teacher_payment_period", type_="unique")
    with op.batch_alter_table("teacher_payments") as batch_op:
        batch_op.create_unique_constraint(
            "uq_teacher_payment_period",
            ["teacher_user_id", "period_start", "period_end"],
        )
