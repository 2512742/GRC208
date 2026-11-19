"""/api/health and the security headers every response must carry (groundwork for T29)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

import app.routers.health as health_module
from app.core.config import get_settings


def test_health_reports_database_ok(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["dialect"] == get_settings().database_dialect
    assert body["time_utc"].endswith("Z")


def test_health_returns_503_without_leaking_details(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    broken = create_engine("postgresql+psycopg://nobody:secret@127.0.0.1:1/none")
    monkeypatch.setattr(health_module, "get_engine", lambda: broken)
    response = client.get("/api/health")
    assert response.status_code == 503
    assert response.json()["database"] == "unavailable"
    assert "secret" not in response.text
    assert "127.0.0.1" not in response.text


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("x-content-type-options", "nosniff"),
        ("x-frame-options", "DENY"),
        ("referrer-policy", "same-origin"),
        ("permissions-policy", "geolocation=(), microphone=(), camera=(), payment=()"),
        ("strict-transport-security", "max-age=31536000; includeSubDomains"),
    ],
)
def test_security_headers_present(client: TestClient, header: str, expected: str) -> None:
    assert client.get("/api/health").headers[header] == expected


def test_app_csp_blocks_external_scripts_and_framing(client: TestClient) -> None:
    csp = client.get("/api/health").headers["content-security-policy"]
    assert "script-src 'self';" in csp
    assert "frame-ancestors 'none'" in csp
    assert "cdn.jsdelivr.net" not in csp


def test_docs_get_their_own_wider_csp(client: TestClient) -> None:
    response = client.get("/api/docs")
    assert response.status_code == 200
    assert "cdn.jsdelivr.net" in response.headers["content-security-policy"]


def test_openapi_schema_served_under_api(client: TestClient) -> None:
    schema = client.get("/api/openapi.json").json()
    assert "/api/health" in schema["paths"]
