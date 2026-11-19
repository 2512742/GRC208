"""Liveness and database check. Used by CI, the Vercel smoke test and before demo recordings."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from app.core.config import get_settings
from app.db import get_engine

router = APIRouter(tags=["health"])
log = logging.getLogger(__name__)


@router.get("/health")
def health(response: Response) -> dict[str, str]:
    settings = get_settings()
    body = {
        "status": "ok",
        "database": "ok",
        "dialect": settings.database_dialect,
        "time_utc": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }
    try:
        with Session(get_engine()) as session:
            session.exec(text("SELECT 1"))  # type: ignore[call-overload]
    except SQLAlchemyError:
        # Log the detail server-side; never leak connection details to the caller.
        log.exception("Database health check failed")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        body["status"] = "degraded"
        body["database"] = "unavailable"
    return body
