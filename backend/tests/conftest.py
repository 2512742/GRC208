"""Test setup.

The test environment is fixed *before* the app is imported, so tests can never touch a real
database: a developer's `.env` may hold the Neon URL, and real environment variables beat `.env`.

- Default: a throwaway SQLite file per test session.
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
os.environ.pop("DATABASE_URL_DIRECT", None)
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
