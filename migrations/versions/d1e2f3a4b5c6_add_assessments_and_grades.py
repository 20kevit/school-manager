"""Add assessment, assessment_result, and grade_history models

Revision ID: d1e2f3a4b5c6
Revises: ce133ab49e4b
Create Date: 2026-08-30

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d1e2f3a4b5c6"
down_revision = "ce133ab49e4b"
branch_labels = None
depends_on = None


def upgrade():
    # assessments table
    op.create_table(
        "assessments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "class_id",
            sa.Integer(),
            sa.ForeignKey("academy_classes.id"),
            nullable=False,
        ),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("scheduled_date", sa.Date(), nullable=True),
        sa.Column("scheduled_time", sa.DateTime(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("max_score", sa.Numeric(10, 2), nullable=False, server_default="100"),
        sa.Column(
            "passing_score", sa.Numeric(10, 2), nullable=False, server_default="60"
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), server_default=""),
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
    op.create_index("ix_assessment_class", "assessments", ["class_id"])
    op.create_index("ix_assessment_type", "assessments", ["type"])
    op.create_index("ix_assessment_status", "assessments", ["status"])
    op.create_index("ix_assessment_date", "assessments", ["scheduled_date"])

    # assessment_results table
    op.create_table(
        "assessment_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "assessment_id",
            sa.Integer(),
            sa.ForeignKey("assessments.id"),
            nullable=False,
        ),
        sa.Column(
            "enrollment_id",
            sa.Integer(),
            sa.ForeignKey("enrollments.id"),
            nullable=False,
        ),
        sa.Column(
            "student_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("score", sa.Numeric(10, 2), nullable=True),
        sa.Column("max_score", sa.Numeric(10, 2), nullable=False, server_default="100"),
        sa.Column("percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "result_status",
            sa.String(20),
            nullable=False,
            server_default="NOT_GRADED",
        ),
        sa.Column(
            "presence_status",
            sa.String(20),
            nullable=False,
            server_default="PRESENT",
        ),
        sa.Column(
            "pass_fail",
            sa.String(20),
            nullable=False,
            server_default="NOT_DETERMINED",
        ),
        sa.Column("comments", sa.Text(), server_default=""),
        sa.Column(
            "graded_by",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("graded_at", sa.DateTime(), nullable=True),
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
    op.create_unique_constraint(
        "uq_result_assessment_enrollment",
        "assessment_results",
        ["assessment_id", "enrollment_id"],
    )
    op.create_index("ix_result_assessment", "assessment_results", ["assessment_id"])
    op.create_index("ix_result_student", "assessment_results", ["student_user_id"])
    op.create_index("ix_result_enrollment", "assessment_results", ["enrollment_id"])
    op.create_index("ix_result_status", "assessment_results", ["result_status"])
    op.create_index("ix_result_passfail", "assessment_results", ["pass_fail"])

    # grade_history table
    op.create_table(
        "grade_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "result_id",
            sa.Integer(),
            sa.ForeignKey("assessment_results.id"),
            nullable=False,
        ),
        sa.Column("previous_score", sa.Numeric(10, 2), nullable=True),
        sa.Column("new_score", sa.Numeric(10, 2), nullable=True),
        sa.Column("previous_pass_fail", sa.String(20), nullable=False),
        sa.Column("new_pass_fail", sa.String(20), nullable=False),
        sa.Column(
            "corrected_by",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("reason", sa.Text(), server_default=""),
        sa.Column(
            "corrected_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_grade_history_result", "grade_history", ["result_id"])
    op.create_index("ix_grade_history_corrected_at", "grade_history", ["corrected_at"])


def downgrade():
    op.drop_table("grade_history")
    op.drop_table("assessment_results")
    op.drop_table("assessments")
