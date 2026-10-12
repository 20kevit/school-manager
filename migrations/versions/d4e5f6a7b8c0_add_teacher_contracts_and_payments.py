"""add teacher contracts and payments

Revision ID: d4e5f6a7b8c0
Revises: b3c4d5e6f7a9
Create Date: 2026-09-01 02:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d4e5f6a7b8c0"
down_revision = "b3c4d5e6f7a9"
branch_labels = None
depends_on = None


def upgrade():
    # Create teacher_contracts table
    op.create_table(
        "teacher_contracts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "teacher_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "class_id",
            sa.Integer(),
            sa.ForeignKey("academy_classes.id"),
            nullable=True,
        ),
        sa.Column("payment_type", sa.String(30), nullable=False),
        sa.Column("rate", sa.Numeric(10, 2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_tc_teacher", "teacher_contracts", ["teacher_user_id"])
    op.create_index("ix_tc_class", "teacher_contracts", ["class_id"])
    op.create_index("ix_tc_active", "teacher_contracts", ["is_active"])

    # Create teacher_payments table
    op.create_table(
        "teacher_payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "teacher_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("gross_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "deductions", sa.Numeric(12, 2), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("net_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_tp_teacher", "teacher_payments", ["teacher_user_id"])
    op.create_index("ix_tp_period", "teacher_payments", ["period_start", "period_end"])
    op.create_index("ix_tp_status", "teacher_payments", ["status"])


def downgrade():
    op.drop_index("ix_tp_status", table_name="teacher_payments")
    op.drop_index("ix_tp_period", table_name="teacher_payments")
    op.drop_index("ix_tp_teacher", table_name="teacher_payments")
    op.drop_table("teacher_payments")

    op.drop_index("ix_tc_active", table_name="teacher_contracts")
    op.drop_index("ix_tc_class", table_name="teacher_contracts")
    op.drop_index("ix_tc_teacher", table_name="teacher_contracts")
    op.drop_table("teacher_contracts")
