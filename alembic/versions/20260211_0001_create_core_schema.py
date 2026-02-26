"""create core schema and query indexes

Revision ID: 20260211_0001
Revises:
Create Date: 2026-02-11 00:01:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260211_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bronze_program",
        sa.Column("program_stream_id", sa.Integer(), nullable=False),
        sa.Column("discipline_id", sa.Integer(), nullable=False),
        sa.Column("discipline_name", sa.String(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("school_name", sa.String(), nullable=False),
        sa.Column("program_stream_name", sa.String(), nullable=False),
        sa.Column("program_site", sa.String(), nullable=False),
        sa.Column("program_stream", sa.String(), nullable=False),
        sa.Column("program_name", sa.String(), nullable=False),
        sa.Column("program_url", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("program_stream_id"),
    )

    op.create_table(
        "bronze_discipline",
        sa.Column("discipline_id", sa.Integer(), nullable=False),
        sa.Column("discipline", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("discipline_id"),
    )

    op.create_table(
        "bronze_description",
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("n_program_description_sections", sa.Integer(), nullable=True),
        sa.Column("program_name", sa.String(), nullable=False),
        sa.Column("match_iteration_name", sa.String(), nullable=True),
        sa.Column("program_contracts", sa.String(), nullable=True),
        sa.Column("general_instructions", sa.String(), nullable=True),
        sa.Column("supporting_documentation_information", sa.String(), nullable=True),
        sa.Column("review_process", sa.String(), nullable=True),
        sa.Column("interviews", sa.String(), nullable=True),
        sa.Column("selection_criteria", sa.String(), nullable=True),
        sa.Column("program_highlights", sa.String(), nullable=True),
        sa.Column("program_curriculum", sa.String(), nullable=True),
        sa.Column("training_sites", sa.String(), nullable=True),
        sa.Column("additional_information", sa.String(), nullable=True),
        sa.Column("return_of_service", sa.String(), nullable=True),
        sa.Column("faq", sa.String(), nullable=True),
        sa.Column("summary_of_changes", sa.String(), nullable=True),
        sa.Column("match_iteration_id", sa.Integer(), nullable=True),
        sa.Column("program_description_id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("document_id"),
    )

    op.create_table(
        "silver_program",
        sa.Column("program_stream_id", sa.Integer(), nullable=False),
        sa.Column("discipline_id", sa.Integer(), nullable=False),
        sa.Column("discipline_name", sa.String(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("school_name", sa.String(), nullable=False),
        sa.Column("program_stream_name", sa.String(), nullable=False),
        sa.Column("program_site", sa.String(), nullable=False),
        sa.Column("program_stream", sa.String(), nullable=False),
        sa.Column("program_name", sa.String(), nullable=False),
        sa.Column("program_url", sa.String(), nullable=True),
        sa.Column("quota", sa.Integer(), nullable=True),
        sa.Column("province", sa.String(), nullable=False),
        sa.Column("is_valid", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("program_stream_id"),
    )

    op.create_table(
        "silver_discipline",
        sa.Column("discipline_id", sa.Integer(), nullable=False),
        sa.Column("discipline", sa.String(), nullable=False),
        sa.Column("province", sa.String(), nullable=True),
        sa.Column("is_valid", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("discipline_id"),
    )

    op.create_table(
        "silver_description_section",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("program_description_id", sa.Integer(), nullable=False),
        sa.Column("program_name", sa.String(), nullable=True),
        sa.Column("section_name", sa.String(), nullable=False),
        sa.Column("section_text", sa.String(), nullable=True),
        sa.Column("is_valid", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "gold_program_profile",
        sa.Column("program_stream_id", sa.Integer(), nullable=False),
        sa.Column("program_name", sa.String(), nullable=False),
        sa.Column("program_stream_name", sa.String(), nullable=False),
        sa.Column("program_stream", sa.String(), nullable=False),
        sa.Column("discipline_name", sa.String(), nullable=False),
        sa.Column("province", sa.String(), nullable=False),
        sa.Column("school_name", sa.String(), nullable=False),
        sa.Column("program_site", sa.String(), nullable=False),
        sa.Column("program_url", sa.String(), nullable=True),
        sa.Column("description_text", sa.String(), nullable=True),
        sa.Column("is_valid", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("program_stream_id"),
    )

    op.create_table(
        "gold_geo_summary",
        sa.Column("province", sa.String(), nullable=False),
        sa.Column("discipline_name", sa.String(), nullable=False),
        sa.Column("program_count", sa.Integer(), nullable=False),
        sa.Column("avg_quota", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("province", "discipline_name"),
    )

    op.create_index("ix_gold_program_profile_province", "gold_program_profile", ["province"])
    op.create_index(
        "ix_gold_program_profile_discipline_name", "gold_program_profile", ["discipline_name"]
    )
    op.create_index("ix_gold_program_profile_school_name", "gold_program_profile", ["school_name"])


def downgrade() -> None:
    op.drop_index("ix_gold_program_profile_school_name", table_name="gold_program_profile")
    op.drop_index("ix_gold_program_profile_discipline_name", table_name="gold_program_profile")
    op.drop_index("ix_gold_program_profile_province", table_name="gold_program_profile")

    op.drop_table("gold_geo_summary")
    op.drop_table("gold_program_profile")
    op.drop_table("silver_description_section")
    op.drop_table("silver_discipline")
    op.drop_table("silver_program")
    op.drop_table("bronze_description")
    op.drop_table("bronze_discipline")
    op.drop_table("bronze_program")
