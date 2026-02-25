import os
from importlib import reload

import numpy as np
from sqlmodel import Session

os.environ.setdefault("DB_URL", "sqlite:///./test_assets_import.db")

import carms.core.database as db
from carms.models.gold import GoldProgramProfile
from carms.pipelines import checks
from carms.pipelines.gold import assets as gold_assets


class StubEmbedder:
    def encode(self, text, normalize_embeddings=True):
        return np.array([0.0, 1.0] + [0.0] * 382)


def setup_db(tmp_path, monkeypatch):
    db_path = tmp_path / "assets.db"
    monkeypatch.setenv("DB_URL", f"sqlite:///{db_path}")
    reload(db)
    db.init_db()
    reload(gold_assets)
    reload(checks)
    return db_path


def test_gold_program_embeddings_asset(tmp_path, monkeypatch):
    setup_db(tmp_path, monkeypatch)
    gold_assets._get_embedding_model.cache_clear()
    gold_assets._get_embedding_model = lambda: StubEmbedder()  # type: ignore

    with Session(db.engine) as session:
        session.add(
            GoldProgramProfile(
                program_stream_id=1,
                program_name="Prog A",
                program_stream_name="Stream A",
                program_stream="CMG",
                discipline_name="Family Medicine",
                province="ON",
                school_name="School A",
                program_site="Toronto, ON",
                program_url=None,
                description_text="Great program",
                is_valid=True,
            )
        )
        session.commit()

    count = gold_assets.gold_program_embeddings(None)
    assert count == 1

    # Asset check should pass when at least one embedding exists.
    result = checks.gold_program_embeddings_not_empty()
    assert result.passed
