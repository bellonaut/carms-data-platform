"""add gold_match_scenario for simulation outputs

Revision ID: 20260212_0003
Revises: 20260212_0002
Create Date: 2026-02-12 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260212_0003"
down_revision = "20260212_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name
    uuid_type = postgresql.UUID(as_uuid=True) if dialect == "postgresql" else sa.String(36)

    op.create_table(
        "gold_match_scenario",
        sa.Column("scenario_id", uuid_type, nullable=False),
        sa.Column("scenario_label", sa.String(), nullable=True),
        sa.Column("scenario_type", sa.String(), nullable=False),
        sa.Column("province", sa.String(), nullable=False),
        sa.Column("discipline_name", sa.String(), nullable=False),
        sa.Column("supply_quota", sa.Integer(), nullable=False),
        sa.Column("demand_mean", sa.Float(), nullable=False),
        sa.Column("fill_rate_mean", sa.Float(), nullable=False),
        sa.Column("fill_rate_p05", sa.Float(), nullable=False),
        sa.Column("fill_rate_p95", sa.Float(), nullable=False),
        sa.Column("iterations", sa.Integer(), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=True),
        sa.Column("params", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("scenario_id", "province", "discipline_name"),
    )
    op.create_index(
        "ix_gold_match_scenario_type",
        "gold_match_scenario",
        ["scenario_type"],
    )
    op.create_index(
        "ix_gold_match_scenario_province",
        "gold_match_scenario",
        ["province"],
    )


def downgrade() -> None:
    op.drop_index("ix_gold_match_scenario_province", table_name="gold_match_scenario")
    op.drop_index("ix_gold_match_scenario_type", table_name="gold_match_scenario")
    op.drop_table("gold_match_scenario")
