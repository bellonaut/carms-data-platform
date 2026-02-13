import os
from importlib import reload

from fastapi.testclient import TestClient

os.environ.setdefault("DB_URL", "sqlite:///./test_api_import.db")

import carms.api.deps as deps
import carms.api.main as main


def _fresh_app(db_url: str | None = None):
    """Reload modules to pick up env changes and return a new FastAPI app."""
    if db_url:
        os.environ["DB_URL"] = db_url
    else:
        os.environ.setdefault("DB_URL", "sqlite:///./test_api.db")
    reload(deps)
    reload(main)
    return main.create_app()


def test_health_endpoint():
    client = TestClient(_fresh_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json().get("status") == "ok"


def test_programs_limit_validation():
    client = TestClient(_fresh_app())
    resp = client.get("/programs", params={"limit": 999})
    assert resp.status_code == 422


def test_programs_province_validation():
    client = TestClient(_fresh_app())
    resp = client.get("/programs", params={"province": "ZZ"})
    assert resp.status_code == 422


def test_api_key_required(monkeypatch):
    monkeypatch.setenv("API_KEY", "secret123")
    client = TestClient(_fresh_app())

    unauthorized = client.get("/health")
    assert unauthorized.status_code == 401

    authorized = client.get("/health", headers={"X-API-Key": "secret123"})
    assert authorized.status_code == 200


def test_rate_limit(monkeypatch):
    # allow only 1 request per window to force a quick 429
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "1")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SEC", "60")
    client = TestClient(_fresh_app())

    first = client.get("/health")
    second = client.get("/health")
    assert first.status_code == 200
    assert second.status_code == 429
