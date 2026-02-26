from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from carms.analytics import preferences
from carms.analytics.simulation import SimulationParams, run_simulation
from carms.api.routes.programs import PROVINCE_PATTERN
from carms.api.schemas import (
    PreferenceResponse,
    PreferenceScore,
    SimulationRequest,
    SimulationResponse,
    SimulationResult,
)
from carms.core.database import get_session
from carms.models.gold import GoldMatchScenario

router = APIRouter(prefix="/analytics", tags=["analytics"])

ALLOWED_TYPES = {"baseline", "quota_shock", "preference_shift"}


def _validate(payload: SimulationRequest) -> None:
    if payload.scenario_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=422, detail="Invalid scenario_type")
    if payload.iterations < 50 or payload.iterations > 2000:
        raise HTTPException(status_code=422, detail="iterations must be between 50 and 2000")
    if payload.quota_multiplier < 0:
        raise HTTPException(status_code=422, detail="quota_multiplier must be non-negative")
    if payload.demand_multiplier < 0:
        raise HTTPException(status_code=422, detail="demand_multiplier must be non-negative")
    if payload.scenario_type == "preference_shift" and not (-0.9 <= payload.shift_pct <= 0.9):
        raise HTTPException(status_code=422, detail="shift_pct must be between -0.9 and 0.9")


def _rows_to_response(rows: list[GoldMatchScenario]) -> SimulationResponse:
    if not rows:
        raise HTTPException(status_code=404, detail="Scenario not found")
    first = rows[0]
    results = [
        SimulationResult(
            province=row.province,
            discipline_name=row.discipline_name,
            supply_quota=row.supply_quota,
            demand_mean=row.demand_mean,
            fill_rate_mean=row.fill_rate_mean,
            fill_rate_p05=row.fill_rate_p05,
            fill_rate_p95=row.fill_rate_p95,
        )
        for row in rows
    ]
    return SimulationResponse(
        scenario_id=first.scenario_id,
        scenario_label=first.scenario_label,
        scenario_type=first.scenario_type,
        iterations=first.iterations,
        seed=first.seed,
        params=first.params,
        results=results,
        created_at=str(first.created_at) if first.created_at else None,
    )


@router.post("/simulate", response_model=SimulationResponse)
def simulate(
    payload: SimulationRequest,
    session: Annotated[Session, Depends(get_session)],
) -> SimulationResponse:
    _validate(payload)
    params = SimulationParams(
        scenario_type=payload.scenario_type,
        scenario_label=payload.scenario_label,
        demand_multiplier=payload.demand_multiplier,
        quota_multiplier=payload.quota_multiplier,
        target_provinces=payload.target_provinces,
        target_disciplines=payload.target_disciplines,
        shift_pct=payload.shift_pct,
        iterations=payload.iterations,
        seed=payload.seed,
        persist=payload.persist,
    )
    _, rows = run_simulation(session, params)
    return _rows_to_response(rows)


@router.get("/simulate/{scenario_id}", response_model=SimulationResponse)
def get_simulation(
    scenario_id: UUID,
    session: Annotated[Session, Depends(get_session)],
) -> SimulationResponse:
    rows = session.exec(
        select(GoldMatchScenario).where(GoldMatchScenario.scenario_id == scenario_id)
    ).all()
    return _rows_to_response(rows)


@router.get("/preferences", response_model=PreferenceResponse)
def preference_scores(
    session: Annotated[Session, Depends(get_session)],
    province: str | None = Query(
        default=None,
        pattern=PROVINCE_PATTERN,
        description="Province code filter (AB|BC|...|UNKNOWN)",
    ),
    discipline: str | None = Query(
        default=None,
        min_length=2,
        description="Discipline substring filter (min length 2)",
    ),
    limit: int = Query(default=50, ge=1, le=200, description="Max number of rows"),
) -> PreferenceResponse:
    try:
        artifact = preferences.ensure_artifact(session)
    except ValueError as exc:  # no programs to train
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    scores = preferences.score_slice(
        session, artifact, province=province, discipline=discipline, limit=limit
    )
    if not scores:
        raise HTTPException(status_code=404, detail="No programs found for slice")

    items: list[PreferenceScore] = [
        PreferenceScore(
            program_stream_id=s.program_stream_id,
            program_name=s.program_name,
            program_stream_name=s.program_stream_name,
            program_stream=s.program_stream,
            discipline_name=s.discipline_name,
            province=s.province,
            score=round(float(s.score), 4),
            feature_values={k: round(float(v), 4) for k, v in s.feature_values.items()},
            label_proxy=round(float(s.label_proxy), 4),
        )
        for s in scores
    ]

    return PreferenceResponse(
        items=items,
        feature_importances={
            k: round(float(v), 4) for k, v in artifact.feature_importances.items()
        },
        model_version=artifact.version,
        filters={"province": province, "discipline": discipline},
    )
