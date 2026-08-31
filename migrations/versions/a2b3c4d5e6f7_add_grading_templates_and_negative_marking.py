"""Add grading templates and negative marking

Revision ID: a2b3c4d5e6f7
Revises: f1e2d3c4b5a6
Create Date: 2026-08-31
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "a2b3c4d5e6f7"
down_revision = "eb6087341015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add penalty_factor to assessments
    op.add_column(
        "assessments",
        sa.Column(
            "penalty_factor", sa.Numeric(4, 2), nullable=False, server_default="0"
        ),
    )

    # Add wrong_count to assessment_results
    op.add_column(
        "assessment_results",
        sa.Column("wrong_count", sa.Integer(), nullable=True),
    )

    # grading_templates
    op.create_table(
        "grading_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "class_id",
            sa.Integer(),
            sa.ForeignKey("academy_classes.id"),
            nullable=False,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_grading_template_class", "grading_templates", ["class_id"])

    # grading_components
    op.create_table(
        "grading_components",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "template_id",
            sa.Integer(),
            sa.ForeignKey("grading_templates.id"),
            nullable=False,
        ),
        sa.Column("assessment_type", sa.String(20), nullable=False),
        sa.Column("weight", sa.Numeric(5, 2), nullable=False),
        sa.UniqueConstraint(
            "template_id",
            "assessment_type",
            name="uq_grading_component_template_type",
        ),
    )
    op.create_index(
        "ix_grading_component_template", "grading_components", ["template_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_grading_component_template", table_name="grading_components")
    op.drop_table("grading_components")
    op.drop_index("ix_grading_template_class", table_name="grading_templates")
    op.drop_table("grading_templates")
    op.drop_column("assessment_results", "wrong_count")
    op.drop_column("assessments", "penalty_factor")
