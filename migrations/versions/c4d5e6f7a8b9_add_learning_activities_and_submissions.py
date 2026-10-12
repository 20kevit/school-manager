"""add learning activities and submissions

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-08-30 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c4d5e6f7a8b9"
down_revision = "b3c4d5e6f7a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Activities table
    op.create_table(
        "activities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "requirement",
            sa.String(length=20),
            nullable=False,
            server_default="REQUIRED",
        ),
        sa.Column("deadline", sa.DateTime(), nullable=True),
        sa.Column("max_score", sa.Numeric(10, 2), nullable=False, server_default="100"),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "course_id",
            sa.Integer(),
            sa.ForeignKey("courses.id"),
            nullable=True,
        ),
        sa.Column(
            "class_id",
            sa.Integer(),
            sa.ForeignKey("academy_classes.id"),
            nullable=True,
        ),
        sa.Column(
            "session_id",
            sa.Integer(),
            sa.ForeignKey("sessions.id"),
            nullable=True,
        ),
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
    op.create_index("ix_activity_course", "activities", ["course_id"])
    op.create_index("ix_activity_class", "activities", ["class_id"])
    op.create_index("ix_activity_session", "activities", ["session_id"])
    op.create_index("ix_activity_type", "activities", ["type"])
    op.create_index("ix_activity_active", "activities", ["is_active"])

    # Activity submissions table
    op.create_table(
        "activity_submissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "activity_id",
            sa.Integer(),
            sa.ForeignKey("activities.id"),
            nullable=False,
        ),
        sa.Column(
            "student_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "enrollment_id",
            sa.Integer(),
            sa.ForeignKey("enrollments.id"),
            nullable=False,
        ),
        sa.Column("text_content", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="NOT_SUBMITTED",
        ),
        sa.Column("score", sa.Numeric(10, 2), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("graded_at", sa.DateTime(), nullable=True),
        sa.Column(
            "graded_by",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
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
    op.create_index("ix_submission_activity", "activity_submissions", ["activity_id"])
    op.create_index(
        "ix_submission_student", "activity_submissions", ["student_user_id"]
    )
    op.create_index(
        "ix_submission_enrollment", "activity_submissions", ["enrollment_id"]
    )
    op.create_index("ix_submission_status", "activity_submissions", ["status"])

    # Activity files table
    op.create_table(
        "activity_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "submission_id",
            sa.Integer(),
            sa.ForeignKey("activity_submissions.id"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_activityfile_submission", "activity_files", ["submission_id"])


def downgrade() -> None:
    op.drop_index("ix_activityfile_submission", table_name="activity_files")
    op.drop_table("activity_files")
    op.drop_index("ix_submission_status", table_name="activity_submissions")
    op.drop_index("ix_submission_enrollment", table_name="activity_submissions")
    op.drop_index("ix_submission_student", table_name="activity_submissions")
    op.drop_index("ix_submission_activity", table_name="activity_submissions")
    op.drop_table("activity_submissions")
    op.drop_index("ix_activity_active", table_name="activities")
    op.drop_index("ix_activity_type", table_name="activities")
    op.drop_index("ix_activity_session", table_name="activities")
    op.drop_index("ix_activity_class", table_name="activities")
    op.drop_index("ix_activity_course", table_name="activities")
    op.drop_table("activities")
