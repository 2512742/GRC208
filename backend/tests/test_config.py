"""Settings: fail-fast on missing secrets, URL normalisation, Neon pooler detection."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings, normalise_database_url

GOOD_SECRET = "x" * 40


def make(**overrides: object) -> Settings:
    """Build settings without reading any .env file."""
    values: dict[str, object] = {"secret_key": GOOD_SECRET}
    values.update(overrides)
    return Settings(_env_file=None, **values)  # type: ignore[arg-type]


def test_missing_secret_key_refuses_to_start(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(ValidationError, match="secret_key"):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_short_secret_key_rejected() -> None:
    with pytest.raises(ValidationError):
        make(secret_key="too-short")


def test_debug_defaults_to_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEBUG", raising=False)
    assert make().debug is False


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("postgresql://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("postgres://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("postgresql+psycopg://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("sqlite:///x.sqlite3", "sqlite:///x.sqlite3"),
    ],
)
def test_database_url_normalised_to_psycopg3(given: str, expected: str) -> None:
    assert normalise_database_url(given) == expected


def test_neon_pooler_detected_and_direct_url_used_for_migrations() -> None:
    pooled = "postgresql://u:p@ep-x-pooler.c-8.us-east-2.aws.neon.tech/neondb?sslmode=require"
    direct = "postgresql://u:p@ep-x.c-8.us-east-2.aws.neon.tech/neondb?sslmode=require"
    s = make(database_url=pooled, database_url_direct=direct)
    assert s.uses_connection_pooler is True
    assert s.is_sqlite is False
    assert s.database_dialect == "postgresql"
    assert s.migration_database_url.startswith("postgresql+psycopg://u:p@ep-x.c-8")


def test_migration_url_falls_back_to_runtime_url() -> None:
    s = make(database_url="sqlite:///a.sqlite3")
    assert s.migration_database_url == "sqlite:///a.sqlite3"
    assert s.uses_connection_pooler is False


def test_org_timezone_defaults_to_lagos_and_rejects_unknown_zones() -> None:
    assert make().org_timezone == "Africa/Lagos"
    with pytest.raises(ValidationError, match="unknown time zone"):
        make(org_timezone="Mars/Olympus_Mons")


def test_serverless_flag_follows_vercel_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VERCEL", raising=False)
    assert make().is_serverless is False
    monkeypatch.setenv("VERCEL", "1")
    assert make().is_serverless is True
