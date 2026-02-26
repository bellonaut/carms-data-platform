import os
from importlib import reload
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session

os.environ.setdefault("DB_URL", "sqlite:///./test_api_analytics_import.db")

import carms.api.deps as deps
import carms.api.main as main
import carms.core.database as db
from carms.models.silver import SilverProgram


def _client(tmp_path):
    db_path = tmp_path / "api_sim.db"
    os.environ["DB_URL"] = f"sqlite:///{db_path}"
    reload(db)
    reload(deps)
    reload(main)
    db.init_db()
    app = main.create_app()
    with Session(db.engine) as session:
        session.add(
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
            )
        )
        session.commit()
    return TestClient(app)


def test_simulate_endpoint_happy_path(tmp_path):
    client = _client(tmp_path)
    resp = client.post(
        "/analytics/simulate",
        json={"scenario_type": "baseline", "iterations": 60, "seed": 1},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "scenario_id" in body
    assert body["results"]
    assert (
        body["results"][0]["fill_rate_p05"]
        <= body["results"][0]["fill_rate_mean"]
        <= body["results"][0]["fill_rate_p95"]
    )


def test_simulate_endpoint_validation(tmp_path):
    client = _client(tmp_path)
    resp = client.post(
        "/analytics/simulate",
        json={"scenario_type": "baseline", "iterations": 10},
    )
    assert resp.status_code == 422


def test_get_simulation_not_found(tmp_path):
    client = _client(tmp_path)
    missing_id = str(uuid4())
    resp = client.get(f"/analytics/simulate/{missing_id}")
    assert resp.status_code == 404
