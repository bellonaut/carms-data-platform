import os
from importlib import reload

os.environ.setdefault("DB_URL", "sqlite:///./test_models_import.db")

import carms.core.database as db


def test_models_importable():
    # Use in-memory sqlite so tests don't need Postgres running
    os.environ["DB_URL"] = "sqlite:///:memory:"
    reload(db)
    db.init_db()
    assert True
