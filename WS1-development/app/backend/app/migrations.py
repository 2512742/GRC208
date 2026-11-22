"""Run Alembic from Python (CLI reset, tests). Same scripts as the `alembic` command."""

from __future__ import annotations

from alembic import command
from alembic.config import Config

from app.core.config import BACKEND_DIR


def alembic_config(url: str) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.attributes["database_url"] = url
    cfg.attributes["configure_logger"] = False
    return cfg


def upgrade(url: str) -> None:
    command.upgrade(alembic_config(url), "head")


def reset(url: str) -> None:
    """Drop every table and rebuild at the latest migration. Destroys all data."""
    cfg = alembic_config(url)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
