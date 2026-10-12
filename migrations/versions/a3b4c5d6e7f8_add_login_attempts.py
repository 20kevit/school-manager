"""add login_attempts table for brute-force protection

Revision ID: a3b4c5d6e7f8
Revises: f7a8b9c0d1e2
Create Date: 2026-10-12 08:00:00.000000

DB-backed login attempt log shared across Gunicorn workers, used by the
login throttling check in app.application.auth.services.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a3b4c5d6e7f8"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "login_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("login", sa.String(150), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=False),
        sa.Column("successful", sa.Boolean(), nullable=False),
        sa.Column(
            "attempted_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Index("ix_login_attempt_login", "login"),
        sa.Index("ix_login_attempt_ip", "ip_address"),
        sa.Index("ix_login_attempt_at", "attempted_at"),
    )


def downgrade() -> None:
    op.drop_table("login_attempts")
