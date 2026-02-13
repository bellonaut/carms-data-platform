import os
from importlib import reload

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

os.environ.setdefault("DB_URL", "sqlite:///./test_preferences_import.db")

import carms.api.deps as deps
import carms.api.main as main
import carms.api.routes.analytics as analytics_route
import carms.core.database as db
from carms.analytics import preferences
from carms.models.gold import GoldProgramEmbedding
from carms.models.silver import SilverProgram


def _seed(session: Session) -> None:
    session.add_all(
        [
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
                discipline_id=10,
                discipline_name="Family Medicine",
                school_id=2,
                school_name="School B",
                program_stream_name="B",
                program_site="Montreal, QC",
                program_stream="IMG",
                program_name="Prog B",
                program_url=None,
                quota=3,
                province="QC",
                is_valid=True,
            ),
            SilverProgram(
                program_stream_id=3,
                discipline_id=20,
                discipline_name="Internal Medicine",
                school_id=3,
                school_name="School C",
                program_stream_name="C",
                program_site="Vancouver, BC",
                program_stream="CMG",
                program_name="Prog C",
                program_url=None,
                quota=2,
                province="BC",
                is_valid=True,
            ),
        ]
    )
    session.add_all(
        [
            GoldProgramEmbedding(
                program_stream_id=1,
                program_name="Prog A",
                program_stream_name="A",
                discipline_name="Family Medicine",
                province="ON",
                description_text="Great program A",
                embedding=[1.0, 0.0],
            ),
            GoldProgramEmbedding(
                program_stream_id=2,
                program_name="Prog B",
                program_stream_name="B",
                discipline_name="Family Medicine",
                province="QC",
                description_text="Great program B",
                embedding=[0.2, 0.8],
            ),
        ]
    )
    session.commit()


def _setup(tmp_path, monkeypatch):
    db_path = tmp_path / "prefs.db"
    artifact_path = tmp_path / "pref_model.json"
    monkeypatch.setenv("DB_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("PREFERENCE_ARTIFACT_PATH", str(artifact_path))
    reload(db)
    reload(preferences)
    reload(deps)
    reload(main)
    reload(analytics_route)
    db.init_db()
    return artifact_path


def test_feature_engineering_values(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    with Session(db.engine) as session:
        _seed(session)
        rows = preferences.build_feature_rows(session)

    by_id = {r.program_stream_id: r for r in rows}
    assert pytest.approx(by_id[1].features["discipline_freq"], rel=1e-3) == 2 / 3
    assert pytest.approx(by_id[1].features["province_mix"], rel=1e-3) == 0.5
    assert by_id[1].features["stream_is_cmg"] == 1.0
    assert by_id[2].features["stream_is_img"] == 1.0
    assert by_id[3].features["embedding_similarity"] == 0.0  # no embedding for program 3


def test_artifact_roundtrip_and_scoring(tmp_path, monkeypatch):
    artifact_path = _setup(tmp_path, monkeypatch)
    with Session(db.engine) as session:
        _seed(session)
        artifact = preferences.train_preference_model(session, persist=True)

    assert artifact_path.exists()
    loaded = preferences.load_artifact()
    assert loaded is not None
    assert pytest.approx(sum(loaded.feature_importances.values()), rel=1e-3) == 1.0

    with Session(db.engine) as session:
        scores = preferences.score_slice(session, loaded, province="ON", discipline="Family")

    assert scores
    assert all(0.0 <= s.score <= 1.0 for s in scores)
    assert scores == sorted(scores, key=lambda x: x.score, reverse=True)


def test_preferences_endpoint_contract_and_validation(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    with Session(db.engine) as session:
        _seed(session)

    client = TestClient(main.create_app())

    resp = client.get("/analytics/preferences", params={"province": "ON", "discipline": "Family"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["model_version"] == preferences.MODEL_VERSION
    assert "feature_importances" in body and body["feature_importances"]
    first = body["items"][0]
    assert first["province"] == "ON"
    assert "score" in first and "feature_values" in first
    assert first["feature_values"]["province_mix"] >= 0

    bad = client.get("/analytics/preferences", params={"province": "ZZ"})
    assert bad.status_code == 422

    short = client.get("/analytics/preferences", params={"discipline": "X"})
    assert short.status_code == 422
