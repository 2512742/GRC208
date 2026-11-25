"""Remote backup database: the live SQLite database is copied in full to PostgreSQL and can be
rebuilt from it (backup-to-postgres, restore-from-backup)."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, make_url, select, text
from sqlalchemy.pool import NullPool
from sqlmodel import Session
from typer.testing import CliRunner

from app.cli import cli
from app.core.config import get_settings
from app.migrations import upgrade
from app.models import AuditLog, Risk, RiskAssessment
from app.services.backup import BackupError, copy_database
from app.services.demo_seed import seed_demo
from tests.conftest import DEMO_PASSWORD


@pytest.fixture(scope="module")
def live_file(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A seeded SQLite file standing in for the VPS database."""
    path = tmp_path_factory.mktemp("live") / "risktrack.sqlite3"
    url = f"sqlite:///{path}"
    upgrade(url)
    engine = create_engine(url, poolclass=NullPool)
    with Session(engine) as session:
        seed_demo(session, DEMO_PASSWORD)
        session.commit()
    engine.dispose()
    return path


@pytest.fixture
def postgres_target() -> Iterator[str]:
    """A separate PostgreSQL database on the test server (only when the suite runs on PG)."""
    base = os.environ["DATABASE_URL"]
    if not base.startswith("postgresql"):
        pytest.skip("needs the PostgreSQL test server (TEST_DATABASE_URL)")
    url = make_url(base)
    name = f"{url.database}_backup_copy"
    admin = create_engine(url, isolation_level="AUTOCOMMIT", poolclass=NullPool)
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    try:
        yield url.set(database=name).render_as_string(hide_password=False)
    finally:
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()


def counts(url: str) -> dict[str, int]:
    engine = create_engine(url, poolclass=NullPool)
    with engine.connect() as conn:
        result = {
            model.__tablename__: conn.execute(select(func.count()).select_from(model)).scalar()  # type: ignore[arg-type]
            for model in (Risk, RiskAssessment, AuditLog)
        }
    engine.dispose()
    return result  # type: ignore[return-value]


def test_restore_into_a_new_sqlite_file(live_file: Path, tmp_path: Path) -> None:
    target = f"sqlite:///{tmp_path / 'restored.sqlite3'}"
    report = copy_database(f"sqlite:///{live_file}", target)
    assert report.rows["risk"] == 22 and report.audit_entries == report.rows["audit_log"] > 0
    assert counts(target) == counts(f"sqlite:///{live_file}")
    # A second copy into the same file is refused rather than mixing rows.
    with pytest.raises(BackupError, match="restore into a new file"):
        copy_database(f"sqlite:///{live_file}", target)


def test_refuses_copying_a_database_onto_itself(live_file: Path) -> None:
    with pytest.raises(BackupError, match="same database"):
        copy_database(f"sqlite:///{live_file}", f"sqlite:///{live_file}")


def test_backup_to_postgres_refreshes_and_restores(
    live_file: Path, postgres_target: str, tmp_path: Path
) -> None:
    source = f"sqlite:///{live_file}"
    first = copy_database(source, postgres_target)
    again = copy_database(source, postgres_target)  # a refresh replaces, never duplicates
    assert first.rows == again.rows
    assert counts(postgres_target) == counts(source)

    # Ids continue after the copied ones, and the insert-only guard is still in force.
    engine = create_engine(postgres_target, poolclass=NullPool)
    with engine.begin() as conn:
        top = conn.execute(select(func.max(AuditLog.id))).scalar()  # type: ignore[arg-type]
        nextval = conn.execute(text("SELECT nextval(pg_get_serial_sequence('audit_log', 'id'))"))
        assert nextval.scalar() == top + 1
    with pytest.raises(Exception, match="insert-only"), engine.begin() as conn:
        conn.execute(text("DELETE FROM risk_assessment"))
    engine.dispose()

    restored = f"sqlite:///{tmp_path / 'from-postgres.sqlite3'}"
    report = copy_database(postgres_target, restored)
    assert report.rows == first.rows
    assert counts(restored) == counts(source)


def test_cli_needs_the_backup_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["backup-to-postgres", "--yes"])
    assert result.exit_code == 2 and "BACKUP_DATABASE_URL is not set" in result.output
    existing = tmp_path / "exists.sqlite3"
    existing.touch()
    monkeypatch.setenv("BACKUP_DATABASE_URL", "postgresql://u:p@backup.example/db")
    get_settings.cache_clear()
    result = runner.invoke(cli, ["restore-from-backup", "--into", str(existing)])
    assert result.exit_code == 1 and "already exists" in result.output
