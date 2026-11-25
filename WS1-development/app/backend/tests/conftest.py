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
    candidates = (settings.backup_database_url, settings.database_url_direct, settings.database_url)
    source = next((u for u in candidates if u and u.startswith("postgresql")), None)
    if source is None:
        raise RuntimeError("TEST_DB=neon needs a Neon URL (BACKUP_DATABASE_URL) in .env")
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
os.environ["BACKUP_DATABASE_URL"] = ""  # tests never reach the real remote backup
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

from sqlalchemy import Connection, Engine  # noqa: E402
from sqlmodel import Session  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[1]


from app.migrations import alembic_config  # noqa: E402,F401  (re-exported for tests)
from app.migrations import reset as migrate_fresh  # noqa: E402  (PG test DB is reused: rebuild)


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


# ── Seeded fixtures (P6): The Alajo seeded once per test module ────────────────────────────


@pytest.fixture(scope="module")
def seeded_connection(migrated_engine: Engine) -> Iterator[Connection]:
    """One connection per module, The Alajo seeded inside an outer transaction that is rolled
    back when the module finishes. Seeding once (not per test) keeps Neon runs practical."""
    from sqlmodel import func, select

    from app.models import AuditLog, Risk
    from app.services.demo_seed import seed_demo

    with migrated_engine.connect() as conn:
        outer = conn.begin()
        with Session(bind=conn, join_transaction_mode="create_savepoint") as session:
            if session.exec(select(func.count()).select_from(Risk)).one():
                pytest.skip("test database already holds risks")
            conn.info["audit_before_seed"] = session.exec(select(func.max(AuditLog.id))).one() or 0
            seed_demo(session, DEMO_PASSWORD)
            session.commit()  # releases into the outer transaction only
        try:
            yield conn
        finally:
            outer.rollback()


@pytest.fixture
def seeded(seeded_connection: Connection) -> Iterator[Session]:
    """Session on the seeded data; everything a test writes (even API commits) is undone."""
    savepoint = seeded_connection.begin_nested()
    with Session(bind=seeded_connection, join_transaction_mode="create_savepoint") as session:
        try:
            yield session
        finally:
            session.close()
            savepoint.rollback()


@pytest.fixture
def seeded_api(seeded: Session) -> Iterator[TestClient]:
    from app.db import get_session

    application = create_app()
    application.dependency_overrides[get_session] = lambda: seeded
    with TestClient(application, base_url="https://testserver") as test_client:
        yield test_client
