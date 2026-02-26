from dagster import AssetIn, asset
from sqlalchemy import func
from sqlmodel import Session, delete, select

from carms.analytics import preferences
from carms.analytics.simulation import SimulationParams, run_simulation
from carms.core.database import engine
from carms.models.gold import GoldMatchScenario

DEFAULT_SCENARIOS: list[SimulationParams] = [
    SimulationParams(scenario_type="baseline", scenario_label="Baseline demand/supply"),
    SimulationParams(
        scenario_type="quota_shock",
        scenario_label="Quota shock 0.8x",
        quota_multiplier=0.8,
    ),
    SimulationParams(
        scenario_type="preference_shift",
        scenario_label="Preference shift +15% to ON/QC",
        target_provinces=["ON", "QC"],
        shift_pct=0.15,
    ),
]


@asset(group_name="analytics", ins={"silver_programs": AssetIn("silver_programs")})
def gold_match_scenarios(silver_programs) -> int:  # type: ignore[unused-argument]
    with Session(engine) as session:
        session.exec(delete(GoldMatchScenario))
        for scenario in DEFAULT_SCENARIOS:
            run_simulation(session, scenario)

        count_stmt = select(func.count()).select_from(GoldMatchScenario)
        total = session.exec(count_stmt).one()
        return total


@asset(group_name="analytics", ins={"silver_programs": AssetIn("silver_programs")})
def preference_model(silver_programs) -> str:  # type: ignore[unused-argument]
    with Session(engine) as session:
        preferences.train_preference_model(session, persist=True)
        return str(preferences.get_artifact_path())
