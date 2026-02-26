from __future__ import annotations

from dataclasses import asdict, dataclass
from uuid import UUID, uuid4

import numpy as np
from sqlmodel import Session, select

from carms.models.gold import GoldMatchScenario
from carms.models.silver import SilverProgram

DIRICHLET_CONC = 50.0


@dataclass
class SimulationParams:
    scenario_type: str
    scenario_label: str | None = None
    demand_multiplier: float = 1.0
    quota_multiplier: float = 1.0
    target_provinces: list[str] | None = None
    target_disciplines: list[str] | None = None
    shift_pct: float = 0.15
    iterations: int = 300
    seed: int | None = None
    persist: bool = True


def _load_supply(session: Session) -> dict[tuple[str, str], int]:
    rows = session.exec(
        select(SilverProgram.province, SilverProgram.discipline_name, SilverProgram.quota)
    ).all()
    supply: dict[tuple[str, str], int] = {}
    for province, discipline, quota in rows:
        key = (province or "UNKNOWN", discipline)
        supply[key] = supply.get(key, 0) + (quota if quota is not None else 1)
    return supply


def _apply_quota_shock(
    supply: dict[tuple[str, str], int],
    multiplier: float,
    target_provinces: list[str] | None,
    target_disciplines: list[str] | None,
) -> dict[tuple[str, str], int]:
    shocked: dict[tuple[str, str], int] = {}
    for key, value in supply.items():
        province, discipline = key
        match_province = not target_provinces or province in target_provinces
        match_discipline = not target_disciplines or discipline in target_disciplines
        if match_province and match_discipline:
            shocked[key] = int(round(value * multiplier))
        else:
            shocked[key] = value
    return shocked


def _apply_preference_shift(
    weights: dict[tuple[str, str], float],
    shift_pct: float,
    target_provinces: list[str] | None,
    target_disciplines: list[str] | None,
) -> dict[tuple[str, str], float]:
    shifted = {}
    for key, value in weights.items():
        province, discipline = key
        match_province = not target_provinces or province in target_provinces
        match_discipline = not target_disciplines or discipline in target_disciplines
        if match_province and match_discipline:
            shifted[key] = max(0.0, value * (1.0 + shift_pct))
        else:
            shifted[key] = value

    total = sum(shifted.values())
    if total == 0:
        return weights
    return {k: v / total for k, v in shifted.items()}


def _dirichlet_weights(
    base_weights: dict[tuple[str, str], float], rng: np.random.Generator
) -> dict[tuple[str, str], float]:
    keys = list(base_weights.keys())
    base = np.array([base_weights[k] for k in keys], dtype=float)
    alpha = base / base.sum() * DIRICHLET_CONC
    draw = rng.dirichlet(alpha)
    return {k: float(v) for k, v in zip(keys, draw, strict=False)}


def _aggregate_results(
    runs: list[dict[tuple[str, str], tuple[int, float]]],
) -> dict[tuple[str, str], dict[str, float]]:
    buckets: dict[tuple[str, str], list[float]] = {}
    demand_totals: dict[tuple[str, str], list[int]] = {}
    for run in runs:
        for key, (demand, fill_rate) in run.items():
            buckets.setdefault(key, []).append(fill_rate)
            demand_totals.setdefault(key, []).append(demand)

    summary: dict[tuple[str, str], dict[str, float]] = {}
    for key, values in buckets.items():
        frates = np.array(values, dtype=float)
        demands = np.array(demand_totals[key], dtype=float)
        summary[key] = {
            "fill_rate_mean": float(frates.mean()),
            "fill_rate_p05": float(np.percentile(frates, 5)),
            "fill_rate_p95": float(np.percentile(frates, 95)),
            "demand_mean": float(demands.mean()),
        }
    return summary


def run_simulation(
    session: Session, params: SimulationParams
) -> tuple[UUID, list[GoldMatchScenario]]:
    rng = np.random.default_rng(params.seed)
    base_supply = _load_supply(session)
    supply = base_supply

    weights: dict[tuple[str, str], float] = {k: float(v) for k, v in base_supply.items()}
    if params.scenario_type == "quota_shock":
        supply = _apply_quota_shock(
            base_supply, params.quota_multiplier, params.target_provinces, params.target_disciplines
        )
    if params.scenario_type == "preference_shift":
        weights = _apply_preference_shift(
            weights, params.shift_pct, params.target_provinces, params.target_disciplines
        )

    total_applicants = int(round(sum(supply.values()) * params.demand_multiplier))
    keys = list(supply.keys())
    supply_vec = {k: max(1, v) for k, v in supply.items()}

    runs: list[dict[tuple[str, str], tuple[int, float]]] = []
    for _ in range(params.iterations):
        draw_weights = _dirichlet_weights(weights, rng)
        probs = np.array([draw_weights[k] for k in keys])
        demand_draw = rng.multinomial(total_applicants, probs)

        run_result: dict[tuple[str, str], tuple[int, float]] = {}
        for key, demand in zip(keys, demand_draw, strict=False):
            quota = supply_vec[key]
            fill_rate = min(demand, quota) / float(quota) if quota > 0 else 0.0
            run_result[key] = (int(demand), float(fill_rate))
        runs.append(run_result)

    summary = _aggregate_results(runs)
    scenario_id = uuid4()
    outputs: list[GoldMatchScenario] = []
    for key, stats in summary.items():
        province, discipline = key
        outputs.append(
            GoldMatchScenario(
                scenario_id=scenario_id,
                scenario_label=params.scenario_label,
                scenario_type=params.scenario_type,
                province=province,
                discipline_name=discipline,
                supply_quota=supply_vec[key],
                demand_mean=stats["demand_mean"],
                fill_rate_mean=stats["fill_rate_mean"],
                fill_rate_p05=stats["fill_rate_p05"],
                fill_rate_p95=stats["fill_rate_p95"],
                iterations=params.iterations,
                seed=params.seed,
                params=asdict(params),
            )
        )

    if params.persist:
        dialect = session.get_bind().dialect.name
        if dialect == "sqlite":
            session.bulk_save_objects(outputs)
            session.commit()
        else:
            session.add_all(outputs)
            session.commit()

    return scenario_id, outputs
