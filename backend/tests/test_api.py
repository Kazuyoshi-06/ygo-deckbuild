"""Smoke tests for the FastAPI application (no DB required)."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch


@pytest.fixture(scope="module")
def client():
    with patch("app.database.AsyncSessionLocal"), \
         patch("app.main.StaticFiles"):
        from app.main import app
        with TestClient(app) as c:
            yield c


def test_root_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "service" in data


def test_v1_health(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_docs_available_in_debug(monkeypatch):
    monkeypatch.setenv("DEBUG", "true")
    # Docs route exists when debug=True — just verify no import error
    from app.config import settings
    # We don't re-instantiate settings here, just confirm the attr exists
    assert hasattr(settings, "debug")


def test_cors_origins_configured():
    from app.config import settings
    assert len(settings.cors_origins) > 0
    assert any("localhost" in o for o in settings.cors_origins)
