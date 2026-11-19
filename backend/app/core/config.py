"""Application settings, read once from environment variables and the repo-root `.env` file.

Lessons carried over from the Guardian project:
- Read one explicit variable per setting (`DATABASE_URL`), never a library helper that silently
  prefers a different source.
- Refuse to start when a required secret is missing, instead of running with a weak default.

Precedence (pydantic-settings): real environment variables win over values in `.env`.
On Vercel everything comes from the project's Environment Variables; locally, from `.env`.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]  # app/backend
REPO_DIR = BACKEND_DIR.parent  # app/ (git repository root)
DEFAULT_SQLITE_URL = f"sqlite:///{BACKEND_DIR / 'risktrack.sqlite3'}"


def normalise_database_url(url: str) -> str:
    """Make any PostgreSQL URL use the psycopg v3 driver; leave other URLs untouched.

    Neon and most hosts hand out `postgresql://...` or `postgres://...`; SQLAlchemy would pick
    psycopg2 for those, which we don't install.
    """
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Required. Used to sign CSRF tokens and derive session secrets. At least 32 characters.
    secret_key: SecretStr = Field(min_length=32)

    debug: bool = False

    # Runtime connection. SQLite by default; Neon's *pooled* URL when hosted.
    database_url: str = DEFAULT_SQLITE_URL
    # Direct (non-pooled) URL for Alembic migrations only. Falls back to database_url.
    database_url_direct: str | None = None

    # The Alajo's official zone: business rules ("today", overdue, expired) use it.
    org_timezone: str = "Africa/Lagos"

    # Optional log file for local runs; never used on serverless hosts.
    log_file: Path | None = None

    @field_validator("database_url", "database_url_direct")
    @classmethod
    def _normalise_url(cls, value: str | None) -> str | None:
        return normalise_database_url(value) if value else value

    @field_validator("org_timezone")
    @classmethod
    def _valid_zone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"unknown time zone: {value!r}") from exc
        return value

    # Derived values -------------------------------------------------------------------------

    @property
    def is_serverless(self) -> bool:
        """True on Vercel (it sets VERCEL=1 in every function)."""
        return bool(os.getenv("VERCEL"))

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def uses_connection_pooler(self) -> bool:
        """Neon pooled endpoints have '-pooler' in the host name (PgBouncer, transaction mode)."""
        return "-pooler" in (urlsplit(self.database_url).hostname or "")

    @property
    def migration_database_url(self) -> str:
        return self.database_url_direct or self.database_url

    @property
    def database_dialect(self) -> str:
        return self.database_url.split(":", 1)[0].split("+", 1)[0]


@lru_cache
def get_settings() -> Settings:
    """Load settings once per process. Raises a validation error if SECRET_KEY is missing."""
    return Settings()  # type: ignore[call-arg]  # values come from the environment
