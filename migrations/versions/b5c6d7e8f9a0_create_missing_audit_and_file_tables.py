"""create missing audit_logs and stored_files tables

Revision ID: b5c6d7e8f9a0
Revises: a3b4c5d6e7f8
Create Date: 2026-10-12 08:30:00.000000

Gap fill: the audit-log and file-metadata models were added without
migrations, so fresh `flask db upgrade` runs never created these tables
(existing databases received them via seed-time create_all instead).

Table creation is guarded by an inspector check so this migration is a
safe no-op on databases that already have the tables (e.g. production),
while fixing fresh installs. Downgrade drops the tables only if present.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b5c6d7e8f9a0"
down_revision = "a3b4c5d6e7f8"
branch_labels = None
depends_on = None


def _existing_tables() -> set:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    existing = _existing_tables()

    if "audit_logs" not in existing:
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False
            ),
            sa.Column("action", sa.String(20), nullable=False),
            sa.Column("entity_type", sa.String(50), nullable=False),
            sa.Column("entity_id", sa.Integer(), nullable=False),
            sa.Column("old_values", sa.JSON(), nullable=True),
            sa.Column("new_values", sa.JSON(), nullable=True),
            sa.Column(
                "timestamp",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Index("ix_audit_user", "user_id"),
            sa.Index("ix_audit_action", "action"),
            sa.Index("ix_audit_entity", "entity_type", "entity_id"),
            sa.Index("ix_audit_timestamp", "timestamp"),
        )

    if "stored_files" not in existing:
        op.create_table(
            "stored_files",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("original_filename", sa.String(255), nullable=False),
            sa.Column("stored_filename", sa.String(255), nullable=False),
            sa.Column("extension", sa.String(20), nullable=False, server_default=""),
            sa.Column(
                "mime_type",
                sa.String(150),
                nullable=False,
                server_default="application/octet-stream",
            ),
            sa.Column("file_size", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "storage_backend", sa.String(20), nullable=False, server_default="local"
            ),
            sa.Column("storage_key", sa.String(500), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
            sa.Column(
                "visibility", sa.String(20), nullable=False, server_default="PRIVATE"
            ),
            sa.Column(
                "category", sa.String(40), nullable=False, server_default="OTHER"
            ),
            sa.Column(
                "uploader_user_id",
                sa.Integer(),
                sa.ForeignKey("users.id"),
                nullable=True,
            ),
            sa.Column("entity_type", sa.String(50), nullable=False, server_default=""),
            sa.Column("entity_id", sa.Integer(), nullable=True),
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
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.Index("ix_storedfile_uploader", "uploader_user_id"),
            sa.Index("ix_storedfile_category", "category"),
            sa.Index("ix_storedfile_status", "status"),
            sa.Index("ix_storedfile_entity", "entity_type", "entity_id"),
            sa.Index("ix_storedfile_created_at", "created_at"),
        )


def downgrade() -> None:
    existing = _existing_tables()
    if "stored_files" in existing:
        op.drop_table("stored_files")
    if "audit_logs" in existing:
        op.drop_table("audit_logs")
