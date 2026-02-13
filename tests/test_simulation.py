import os
from importlib import reload

import numpy as np
from sqlmodel import Session

os.environ.setdefault("DB_URL", "sqlite:///./test_sim_import.db")

import carms.core.database as db
from carms.analytics.simulation import SimulationParams, run_simulation
from carms.models.gold import GoldMatchScenario
from carms.models.silver import SilverProgram


def setup_db(tmp_path, monkeypatch):
    db_path = tmp_path / "sim.db"
    monkeypatch.setenv("DB_URL", f"sqlite:///{db_path}")
    reload(db)
    db.init_db()
    return db_path


def seed_supply():
    return [
        SilverProgram(
            program_stream_id=1,
            discipline_id=10,
            discipline_name="Family Medicine",
            school_id=1,
            school_name="School A",
            program_stream_name="A",
            program_site="Toronto, ON",
            program_stream="CMG",
            program_name="Prog A",
            program_url=None,
            quota=5,
            province="ON",
            is_valid=True,
        ),
        SilverProgram(
            program_stream_id=2,
            discipline_id=20,
            discipline_name="Internal Medicine",
            school_id=2,
            school_name="School B",
            program_stream_name="B",
            program_site="Montreal, QC",
            program_stream="CMG",
            program_name="Prog B",
            program_url=None,
            quota=5,
            province="QC",
            is_valid=True,
        ),
    ]


def test_simulation_deterministic(tmp_path, monkeypatch):
    setup_db(tmp_path, monkeypatch)
    with Session(db.engine) as session:
        session.add_all(seed_supply())
        session.commit()

        params = SimulationParams(scenario_type="baseline", iterations=200, seed=42)
        _, rows1 = run_simulation(session, params)
        # run without persisting to avoid double insert
        params.persist = False
        _, rows2 = run_simulation(session, params)

    def stats(rows):
        by_key = {(r.province, r.discipline_name): r for r in rows}
        return {
            k: (
                round(v.fill_rate_mean, 4),
                round(v.fill_rate_p05, 4),
                round(v.fill_rate_p95, 4),
            )
            for k, v in by_key.items()
        }

    assert stats(rows1) == stats(rows2)


def test_quota_shock_zero_yields_zero_fill(tmp_path, monkeypatch):
    setup_db(tmp_path, monkeypatch)
    with Session(db.engine) as session:
        session.add_all(seed_supply())
        session.commit()

        params = SimulationParams(
            scenario_type="quota_shock",
            quota_multiplier=0.0,
            iterations=50,
            seed=1,
        )
        _, rows = run_simulation(session, params)

    assert all(r.fill_rate_mean == 0.0 for r in rows)


def test_preference_shift_moves_demand(tmp_path, monkeypatch):
    setup_db(tmp_path, monkeypatch)
    with Session(db.engine) as session:
        session.add_all(seed_supply())
        session.commit()

        base_params = SimulationParams(scenario_type="baseline", iterations=200, seed=10, persist=False)
        _, base_rows = run_simulation(session, base_params)

        shift_params = SimulationParams(
            scenario_type="preference_shift",
            target_provinces=["ON"],
            shift_pct=0.5,
            iterations=200,
            seed=10,
            persist=False,
        )
        _, shifted_rows = run_simulation(session, shift_params)

    base_on = next(r for r in base_rows if r.province == "ON")
    shifted_on = next(r for r in shifted_rows if r.province == "ON")
    assert shifted_on.demand_mean > base_on.demand_mean
