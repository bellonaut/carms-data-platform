from uuid import UUID

from pydantic import BaseModel


class ProgramListItem(BaseModel):
    program_stream_id: int
    program_name: str
    program_stream_name: str
    program_stream: str
    discipline_name: str
    school_name: str
    program_site: str
    program_url: str | None = None
    province: str
    is_valid: bool

    # list-friendly
    description_preview: str | None = None


class ProgramDetail(ProgramListItem):
    # detail view includes full text
    description_text: str | None = None


class ProgramListResponse(BaseModel):
    items: list[ProgramListItem]
    limit: int
    offset: int
    total: int | None = None


class SemanticQueryRequest(BaseModel):
    query: str
    province: str | None = None
    discipline: str | None = None
    top_k: int = 5


class SemanticHit(BaseModel):
    program_stream_id: int
    program_name: str
    program_stream_name: str
    discipline_name: str
    province: str
    similarity: float
    description_snippet: str | None = None


class SemanticQueryResponse(BaseModel):
    hits: list[SemanticHit]
    answer: str | None = None
    top_k: int


class SimulationRequest(BaseModel):
    scenario_label: str | None = None
    scenario_type: str
    demand_multiplier: float = 1.0
    quota_multiplier: float = 1.0
    target_provinces: list[str] | None = None
    target_disciplines: list[str] | None = None
    shift_pct: float = 0.15
    iterations: int = 300
    seed: int | None = None
    persist: bool = True


class SimulationResult(BaseModel):
    province: str
    discipline_name: str
    supply_quota: int
    demand_mean: float
    fill_rate_mean: float
    fill_rate_p05: float
    fill_rate_p95: float


class SimulationResponse(BaseModel):
    scenario_id: UUID
    scenario_type: str
    scenario_label: str | None = None
    iterations: int
    seed: int | None = None
    params: dict | None = None
    results: list[SimulationResult]
    created_at: str | None = None


class PreferenceScore(BaseModel):
    program_stream_id: int
    program_name: str
    program_stream_name: str
    program_stream: str
    discipline_name: str
    province: str
    score: float
    feature_values: dict[str, float]
    label_proxy: float


class PreferenceResponse(BaseModel):
    items: list[PreferenceScore]
    feature_importances: dict[str, float]
    model_version: str
    filters: dict[str, str | None]
