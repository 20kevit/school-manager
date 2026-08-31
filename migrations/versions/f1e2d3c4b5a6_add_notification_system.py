"""Add notification system tables

Revision ID: f1e2d3c4b5a6
Revises: d1e2f3a4b5c6
Create Date: 2026-08-30
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "f1e2d3c4b5a6"
down_revision = "d1e2f3a4b5c6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # notification_templates
    op.create_table(
        "notification_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("notification_type", sa.String(40), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("subject", sa.String(200), server_default=""),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")
        ),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_template_type", "notification_templates", ["notification_type"])
    op.create_index("ix_template_channel", "notification_templates", ["channel"])
    op.create_index("ix_template_active", "notification_templates", ["is_active"])

    # notifications
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("notification_type", sa.String(40), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "recipient_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("priority", sa.String(10), nullable=False, server_default="NORMAL"),
        sa.Column(
            "template_id",
            sa.Integer(),
            sa.ForeignKey("notification_templates.id"),
            nullable=True,
        ),
        sa.Column("event_key", sa.String(200), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("scheduled_at", sa.DateTime(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("failed_at", sa.DateTime(), nullable=True),
        sa.Column("failure_reason", sa.Text(), server_default=""),
        sa.Column(
            "retry_count", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_notification_recipient", "notifications", ["recipient_user_id"])
    op.create_index("ix_notification_status", "notifications", ["status"])
    op.create_index("ix_notification_type", "notifications", ["notification_type"])
    op.create_index("ix_notification_created_at", "notifications", ["created_at"])
    op.create_index("ix_notification_event_key", "notifications", ["event_key"])

    # notification_deliveries
    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "notification_id",
            sa.Integer(),
            sa.ForeignKey("notifications.id"),
            nullable=False,
        ),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("provider_name", sa.String(50), server_default=""),
        sa.Column("provider_message_id", sa.String(200), server_default=""),
        sa.Column("failure_reason", sa.Text(), server_default=""),
        sa.Column(
            "attempt_count", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("failed_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint(
            "notification_id", "channel", name="uq_delivery_notification_channel"
        ),
    )
    op.create_index(
        "ix_delivery_notification", "notification_deliveries", ["notification_id"]
    )
    op.create_index("ix_delivery_channel", "notification_deliveries", ["channel"])
    op.create_index("ix_delivery_status", "notification_deliveries", ["status"])

    # notification_preferences
    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("notification_type", sa.String(40), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint(
            "user_id",
            "notification_type",
            "channel",
            name="uq_preference_user_type_channel",
        ),
    )
    op.create_index("ix_preference_user", "notification_preferences", ["user_id"])

    # in_app_notifications
    op.create_table(
        "in_app_notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "notification_id",
            sa.Integer(),
            sa.ForeignKey("notifications.id"),
            nullable=True,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "notification_type",
            sa.String(40),
            nullable=False,
            server_default="IN_APP_MESSAGE",
        ),
        sa.Column("link", sa.String(500), server_default=""),
        sa.Column(
            "read_status", sa.String(10), nullable=False, server_default="UNREAD"
        ),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_inapp_user", "in_app_notifications", ["user_id"])
    op.create_index("ix_inapp_read_status", "in_app_notifications", ["read_status"])
    op.create_index("ix_inapp_created_at", "in_app_notifications", ["created_at"])


def downgrade() -> None:
    op.drop_table("in_app_notifications")
    op.drop_table("notification_preferences")
    op.drop_table("notification_deliveries")
    op.drop_table("notifications")
    op.drop_table("notification_templates")
