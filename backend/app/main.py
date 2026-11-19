"""RiskTrack API entry point.

Run locally:   uvicorn app.main:app --reload        (from app/backend)
On Vercel:     api/index.py imports `app` from here.

All API routes live under /api. Later phases also serve the built React app from here for
local single-URL runs (PLAN.md §3).
"""

from __future__ import annotations

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.headers import SecurityHeadersMiddleware
from app.core.logging import configure_logging
from app.routers import health

API_PREFIX = "/api"


def create_app() -> FastAPI:
    settings = get_settings()  # fails fast if SECRET_KEY is missing
    configure_logging(settings)

    application = FastAPI(
        title="RiskTrack API",
        summary="Cyber Risk Register and Treatment Management Platform (GRC208 Group 1)",
        version="0.1.0",
        docs_url=f"{API_PREFIX}/docs",
        redoc_url=f"{API_PREFIX}/redoc",
        openapi_url=f"{API_PREFIX}/openapi.json",
    )
    application.add_middleware(SecurityHeadersMiddleware, hsts=not settings.debug)
    application.include_router(health.router, prefix=API_PREFIX)
    return application


app = create_app()
