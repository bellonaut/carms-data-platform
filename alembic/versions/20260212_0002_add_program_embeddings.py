"""add gold_program_embedding table for semantic search

Revision ID: 20260212_0002
Revises: 20260211_0001
Create Date: 2026-02-12 06:30:00.000000
"""

import sqlalchemy as sa

from alembic import op

try:  # pragma: no cover
    from pgvector.sqlalchemy import Vector
except Exception:  # pragma: no cover
    Vector = None  # type: ignore

# revision identifiers, used by Alembic.
revision = "20260212_0002"
down_revision = "20260211_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name

    embedding_type = sa.JSON()
    if dialect == "postgresql" and Vector is not None:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        embedding_type = Vector(384)

    op.create_table(
        "gold_program_embedding",
        sa.Column("program_stream_id", sa.Integer(), nullable=False),
        sa.Column("program_name", sa.String(), nullable=False),
        sa.Column("program_stream_name", sa.String(), nullable=False),
        sa.Column("discipline_name", sa.String(), nullable=False),
        sa.Column("province", sa.String(), nullable=False),
        sa.Column("description_text", sa.Text(), nullable=True),
        sa.Column("embedding", embedding_type, nullable=False),
        sa.PrimaryKeyConstraint("program_stream_id"),
    )

    op.create_index("ix_gold_program_embedding_province", "gold_program_embedding", ["province"])
    op.create_index(
        "ix_gold_program_embedding_discipline_name", "gold_program_embedding", ["discipline_name"]
    )

    # Optional vector index to speed similarity search; ivfflat requires ANALYZE after load.
    if dialect == "postgresql":
        op.create_index(
            "ix_gold_program_embedding_embedding_cosine",
            "gold_program_embedding",
            ["embedding"],
            postgresql_using="ivfflat",
            postgresql_ops={"embedding": "vector_cosine_ops"},
            postgresql_with={"lists": 50},
        )


def downgrade() -> None:
    op.drop_index(
        "ix_gold_program_embedding_embedding_cosine",
        table_name="gold_program_embedding",
        if_exists=True,
    )
    op.drop_index("ix_gold_program_embedding_discipline_name", table_name="gold_program_embedding")
    op.drop_index("ix_gold_program_embedding_province", table_name="gold_program_embedding")
    op.drop_table("gold_program_embedding")
