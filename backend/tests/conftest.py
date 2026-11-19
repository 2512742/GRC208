"""Test setup.

The test environment is fixed *before* the app is imported, so tests can never touch a real
database: a developer's `.env` may hold the Neon URL, and real environment variables beat `.env`.

- Default: a throwaway SQLite file per test session.
- DATABASE_URL_DIRECT is forced empty so migrations also go to the test database.
- `TEST_DB=neon pytest` runs against the Neon database `risktrack_test` (same server as the
  URLs in `.env`, never `neondb`).
- CI's PostgreSQL job sets TEST_DATABASE_URL to its `postgres:18` service container.
- Safety: tests refuse any PostgreSQL database whose name doesn't contain "test", because the
  suite drops and rebuilds the whole schema.
"""

from __future__ import annotations

import atexit
import os
import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import make_url  # noqa: E402

NEON_TEST_DATABASE = "risktrack_test"


def _neon_test_url() -> str:
    """Neon URL for the test database, derived from the direct URL in `.env`."""
    from app.core.config import Settings

    settings = Settings()  # type: ignore[call-arg]  # reads .env
    if settings.is_sqlite:
        raise RuntimeError("TEST_DB=neon needs the Neon URLs in .env")
    source = settings.database_url_direct or settings.database_url  # direct: tests run DDL
    url = make_url(source).set(database=NEON_TEST_DATABASE)
    return url.render_as_string(hide_password=False)


if os.environ.get("TEST_DB", "").lower() == "neon" and "TEST_DATABASE_URL" not in os.environ:
    os.environ["TEST_DATABASE_URL"] = _neon_test_url()

if "TEST_DATABASE_URL" in os.environ:
    _name = make_url(os.environ["TEST_DATABASE_URL"]).database or ""
    if "test" not in _name.lower():
        raise RuntimeError(
            f"Refusing to run tests on database {_name!r}: the suite drops the schema. "
            "Use a database whose name contains 'test'."
        )

_tmp_dir = Path(tempfile.mkdtemp(prefix="risktrack-tests-"))
atexit.register(shutil.rmtree, _tmp_dir, ignore_errors=True)  # remove the throwaway DB afterwards
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


# ── API fixtures (P3) ───────────────────────────────────────────────────────────────────────

DEMO_PASSWORD = "Alajo-Demo-2026!"
_DEMO_HASH: str | None = None


@pytest.fixture
def api(db: Session) -> Iterator[TestClient]:
    """HTTPS test client whose requests share the test's rolled-back transaction."""
    from app.db import get_session

    application = create_app()
    application.dependency_overrides[get_session] = lambda: db
    with TestClient(application, base_url="https://testserver") as test_client:
        yield test_client


@pytest.fixture
def people(db: Session) -> dict[str, object]:
    """The demo personas (PLAN.md §4.3), all with DEMO_PASSWORD."""
    import app.services.users as users_service
    from app.core.security import hash_password
    from app.models.enums import Role

    global _DEMO_HASH
    if _DEMO_HASH is None:
        _DEMO_HASH = hash_password(DEMO_PASSWORD)  # Argon2 is slow on purpose: hash once
    real_hash = users_service.hash_password
    users_service.hash_password = lambda pw: _DEMO_HASH if pw == DEMO_PASSWORD else real_hash(pw)

    cast = {
        "admin": ("System Administrator", Role.ADMIN),
        "omotayo": ("Omotayo Akinola", Role.ANALYST),
        "emmanuel": ("Emmanuel Teye Adjei", Role.OWNER),
        "anita": ("Anita Ojimba", Role.OWNER),
        "adeola": ("Adeola Bamigboye", Role.APPROVER),
        "kelechi": ("Kelechi Kenneth Nwankwo", Role.APPROVER),
        "ernestina": ("Ernestina Lamiorkor Tawiah", Role.AUDITOR),
    }
    try:
        users = {
            name: users_service.create_user(
                db, username=name, full_name=full, role=role, password=DEMO_PASSWORD
            )
            for name, (full, role) in cast.items()
        }
    finally:
        users_service.hash_password = real_hash
    db.commit()  # commits the savepoint only; still rolled back after the test
    return users  # type: ignore[return-value]


def sign_in(client: TestClient, username: str, password: str = DEMO_PASSWORD) -> str:
    """Log in and make the client send the CSRF header from now on. Returns the token."""
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    token = response.json()["csrf_token"]
    client.headers["X-CSRF-Token"] = token
    return token
