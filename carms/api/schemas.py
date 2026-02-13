from typing import Dict, List, Optional
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
    program_url: Optional[str] = None
    province: str
    is_valid: bool

    # list-friendly
    description_preview: Optional[str] = None


class ProgramDetail(ProgramListItem):
    # detail view includes full text
    description_text: Optional[str] = None


class ProgramListResponse(BaseModel):
    items: List[ProgramListItem]
    limit: int
    offset: int
    total: Optional[int] = None


class SemanticQueryRequest(BaseModel):
    query: str
    province: Optional[str] = None
    discipline: Optional[str] = None
    top_k: int = 5


class SemanticHit(BaseModel):
    program_stream_id: int
    program_name: str
    program_stream_name: str
    discipline_name: str
    province: str
    similarity: float
    description_snippet: Optional[str] = None


class SemanticQueryResponse(BaseModel):
    hits: List[SemanticHit]
    answer: Optional[str] = None
    top_k: int


class SimulationRequest(BaseModel):
    scenario_label: Optional[str] = None
    scenario_type: str
    demand_multiplier: float = 1.0
    quota_multiplier: float = 1.0
    target_provinces: Optional[List[str]] = None
    target_disciplines: Optional[List[str]] = None
    shift_pct: float = 0.15
    iterations: int = 300
    seed: Optional[int] = None
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
    scenario_label: Optional[str] = None
    iterations: int
    seed: Optional[int] = None
    params: Optional[dict] = None
    results: List[SimulationResult]
    created_at: Optional[str] = None


class PreferenceScore(BaseModel):
    program_stream_id: int
    program_name: str
    program_stream_name: str
    program_stream: str
    discipline_name: str
    province: str
    score: float
    feature_values: Dict[str, float]
    label_proxy: float


class PreferenceResponse(BaseModel):
    items: List[PreferenceScore]
    feature_importances: Dict[str, float]
    model_version: str
    filters: Dict[str, Optional[str]]
