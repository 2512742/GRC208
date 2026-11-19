"""Test setup.

The test environment is fixed *before* the app is imported, so tests can never touch a real
database: a developer's `.env` may hold the Neon URL, and real environment variables beat `.env`.

- Default: a throwaway SQLite file per test session.
- DATABASE_URL_DIRECT is forced empty so migrations also go to the test database.
- CI's PostgreSQL job sets TEST_DATABASE_URL to its `postgres:18` service container.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

_tmp_dir = Path(tempfile.mkdtemp(prefix="risktrack-tests-"))
os.environ["SECRET_KEY"] = "test-secret-key-that-is-at-least-32-characters-long"
os.environ["DEBUG"] = "false"
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", f"sqlite:///{_tmp_dir / 'test.sqlite3'}"
)
# Empty (not removed): a real env var beats the developer's .env, which may hold Neon URLs.
os.environ["DATABASE_URL_DIRECT"] = ""
os.environ.pop("VERCEL", None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db import get_engine  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def _fresh_caches() -> Iterator[None]:
    """Each test starts with settings and engine rebuilt from the environment above."""
    _reset()
    yield
    _reset()


def _reset() -> None:
    if get_engine.cache_info().currsize:
        get_engine().dispose()  # close pooled connections before forgetting the engine
    get_engine.cache_clear()
    get_settings.cache_clear()


# ── Database fixtures (P1) ──────────────────────────────────────────────────────────────────

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import Connection, Engine  # noqa: E402
from sqlmodel import Session  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[1]


def alembic_config(url: str) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.attributes["database_url"] = url
    cfg.attributes["configure_logger"] = False
    return cfg


def migrate_fresh(url: str) -> None:
    """Drop everything (the PostgreSQL test DB is reused between runs) and rebuild to head."""
    cfg = alembic_config(url)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")


@pytest.fixture(scope="session")
def migrated_engine() -> Iterator[Engine]:
    from app.core.config import Settings
    from app.db import build_engine

    url = os.environ["DATABASE_URL"]
    migrate_fresh(url)
    engine = build_engine(Settings())  # type: ignore[call-arg]
    yield engine
    engine.dispose()


@pytest.fixture
def connection(migrated_engine: Engine) -> Iterator[Connection]:
    """A connection inside a transaction that is always rolled back: tests leave no data."""
    with migrated_engine.connect() as conn:
        outer = conn.begin()
        try:
            yield conn
        finally:
            outer.rollback()


@pytest.fixture
def db(connection: Connection) -> Iterator[Session]:
    """ORM session on the rolled-back connection. Use `expect_db_error` for failing writes."""
    with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
        yield session
