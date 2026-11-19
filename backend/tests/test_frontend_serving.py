"""The built React app is served from FastAPI for single-URL runs, without shadowing the API."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.headers import SecurityHeadersMiddleware
from app.frontend import mount_frontend


def make_app(tmp_path: Path) -> TestClient:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><div id=root></div>", encoding="utf-8")
    (dist / "assets" / "index-abc.js").write_text("console.log(1)", encoding="utf-8")
    (dist / "theme-init.js").write_text("// theme", encoding="utf-8")
    (dist / "sw.js").write_text("// service worker", encoding="utf-8")
    (dist / "manifest.webmanifest").write_text('{"name": "RiskTrack"}', encoding="utf-8")
    (tmp_path / "secret.txt").write_text("nope", encoding="utf-8")
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware, hsts=True)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    assert mount_frontend(app, dist)
    return TestClient(app)


def test_spa_routes_serve_the_app_shell(tmp_path: Path) -> None:
    client = make_app(tmp_path)
    for path in ("/", "/risks/R-013", "/approvals?view=expired"):
        response = client.get(path)
        assert response.status_code == 200 and "id=root" in response.text
        assert response.headers["cache-control"] == "no-cache"
        assert "script-src 'self'" in response.headers["content-security-policy"]


def test_static_files_and_cache_headers(tmp_path: Path) -> None:
    client = make_app(tmp_path)
    asset = client.get("/assets/index-abc.js")
    assert asset.status_code == 200 and "immutable" in asset.headers["cache-control"]
    assert client.get("/theme-init.js").headers["cache-control"] == "no-cache"


def test_api_paths_are_never_shadowed(tmp_path: Path) -> None:
    client = make_app(tmp_path)
    assert client.get("/api/health").json() == {"status": "ok"}
    missing = client.get("/api/nope")
    assert missing.status_code == 404 and missing.json() == {"detail": "Not Found"}


def test_no_files_outside_dist(tmp_path: Path) -> None:
    client = make_app(tmp_path)
    for path in ("/../secret.txt", "/%2e%2e/secret.txt", "/assets/../../secret.txt"):
        response = client.get(path)
        assert "nope" not in response.text


def test_not_mounted_without_a_build(tmp_path: Path) -> None:
    assert mount_frontend(FastAPI(), tmp_path / "missing") is False


def test_vercel_static_headers_match_the_api() -> None:
    """On Vercel the React files bypass FastAPI, so vercel.json repeats the headers (T29)."""
    import json

    from app.core.config import REPO_DIR
    from app.core.headers import APP_CSP, BASE_HEADERS

    config = json.loads((REPO_DIR / "vercel.json").read_text(encoding="utf-8"))
    rule = next(r for r in config["headers"] if r["source"] == "/(.*)")
    headers = {h["key"]: h["value"] for h in rule["headers"]}
    assert headers["Content-Security-Policy"] == APP_CSP
    for name, value in BASE_HEADERS.items():
        assert headers[name] == value
    assert config["rewrites"][0] == {"source": "/api/(.*)", "destination": "/api/index"}


def test_pwa_files_served_correctly(tmp_path: Path) -> None:
    """The service worker must never be cached (so updates arrive) and the manifest needs its
    media type; both stay under the same strict CSP."""
    client = make_app(tmp_path)
    worker = client.get("/sw.js")
    assert worker.status_code == 200 and worker.headers["cache-control"] == "no-cache"
    assert "javascript" in worker.headers["content-type"]
    manifest = client.get("/manifest.webmanifest")
    assert manifest.headers["content-type"].startswith("application/manifest+json")
    assert "script-src 'self'" in manifest.headers["content-security-policy"]


def test_head_requests_answered(tmp_path: Path) -> None:
    client = make_app(tmp_path)
    assert client.head("/").status_code == 200
    assert client.head("/risks/R-013").status_code == 200
