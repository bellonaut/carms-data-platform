import os
from importlib import reload

import numpy as np
from fastapi.testclient import TestClient
from sqlmodel import Session

os.environ.setdefault("DB_URL", "sqlite:///./test_semantic_import.db")

import carms.api.deps as deps
import carms.api.main as main
import carms.api.routes.semantic as semantic
import carms.core.database as db
from carms.models.gold import GoldProgramEmbedding


class StubModel:
    def encode(self, text, normalize_embeddings=True):
        return np.array([1.0, 0.0])


def _client(tmp_path):
    db_path = tmp_path / "semantic.db"
    os.environ["DB_URL"] = f"sqlite:///{db_path}"
    reload(db)
    reload(deps)
    reload(main)
    reload(semantic)
    db.init_db()
    # stub sentence transformer
    semantic._get_model.cache_clear()
    semantic._get_model = lambda: StubModel()  # type: ignore
    app = main.create_app()
    with Session(db.engine) as session:
        session.add(
            GoldProgramEmbedding(
                program_stream_id=1,
                program_name="Prog A",
                program_stream_name="Stream A",
                discipline_name="Family Medicine",
                province="ON",
                description_text="Great program",
                embedding=[1.0, 0.0],
            )
        )
        session.commit()
    return TestClient(app)


def test_semantic_query_success(tmp_path):
    client = _client(tmp_path)
    resp = client.post("/semantic/query", json={"query": "family medicine", "top_k": 3})
    assert resp.status_code == 200
    body = resp.json()
    assert body["hits"]
    assert body["hits"][0]["similarity"] >= 0.9


def test_semantic_query_validation(tmp_path):
    client = _client(tmp_path)
    resp = client.post("/semantic/query", json={"query": "x", "top_k": 30})
    assert resp.status_code == 422
