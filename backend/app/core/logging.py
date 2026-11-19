"""Logging: always to the console (Vercel captures stdout); to a file only on local runs that ask
for one (Guardian's `if not VERCEL` pattern)."""

from __future__ import annotations

import logging

from app.core.config import Settings

LOG_FORMAT = "%(levelname)s %(asctime)s %(name)s %(message)s"


def configure_logging(settings: Settings) -> None:
    root = logging.getLogger()
    if getattr(root, "_risktrack_configured", False):
        return

    level = logging.DEBUG if settings.debug else logging.INFO
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if settings.log_file and not settings.is_serverless:
        settings.log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(settings.log_file, encoding="utf-8"))

    formatter = logging.Formatter(LOG_FORMAT)
    for handler in handlers:
        handler.setFormatter(formatter)
        root.addHandler(handler)
    root.setLevel(level)
    root._risktrack_configured = True  # type: ignore[attr-defined]
