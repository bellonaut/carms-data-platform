from uuid import UUID

import sqlalchemy as sa
from sqlmodel import Field, SQLModel

# Prefer pgvector on Postgres; fall back to JSON for SQLite to keep tests green.
try:  # pragma: no cover
    from pgvector.sqlalchemy import Vector
except Exception:  # pragma: no cover
    Vector = None  # type: ignore


def _embedding_column():
    if Vector is not None:
        return sa.Column(Vector(384))
    return sa.Column(sa.JSON)


class GoldProgramProfile(SQLModel, table=True):
    __tablename__ = "gold_program_profile"
    program_stream_id: int = Field(primary_key=True)
    program_name: str
    program_stream_name: str
    program_stream: str
    discipline_name: str = Field(index=True)
    province: str = Field(default="UNKNOWN", index=True)
    school_name: str = Field(index=True)
    program_site: str
    program_url: str | None = None
    description_text: str | None = None
    is_valid: bool = True


class GoldGeoSummary(SQLModel, table=True):
    __tablename__ = "gold_geo_summary"
    province: str = Field(primary_key=True)
    discipline_name: str = Field(primary_key=True)
    program_count: int
    avg_quota: float | None = None


class GoldProgramEmbedding(SQLModel, table=True):
    __tablename__ = "gold_program_embedding"

    program_stream_id: int = Field(primary_key=True)
    program_name: str
    program_stream_name: str
    discipline_name: str = Field(index=True)
    province: str = Field(index=True)
    description_text: str | None = None
    embedding: list[float] = Field(sa_column=_embedding_column())


class GoldMatchScenario(SQLModel, table=True):
    __tablename__ = "gold_match_scenario"

    scenario_id: UUID = Field(primary_key=True)
    scenario_label: str | None = None
    scenario_type: str = Field(index=True)
    province: str = Field(index=True)
    discipline_name: str = Field(index=True)
    supply_quota: int
    demand_mean: float
    fill_rate_mean: float
    fill_rate_p05: float
    fill_rate_p95: float
    iterations: int
    seed: int | None = None
    params: dict | None = Field(default=None, sa_column=sa.Column(sa.JSON))
    created_at: str | None = Field(
        sa_column=sa.Column(sa.DateTime(timezone=True), server_default=sa.func.now())
    )
