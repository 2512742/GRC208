"""Backups: a JSON file of every table (`export-backup`) and a full copy to the remote PostgreSQL
backup database (`backup-to-postgres`, `restore-from-backup`).

The JSON export is version-independent (no pg_dump client/server mismatch, a lesson from the
Guardian project's Render migration). Evidence bytes are base64-encoded. The file holds personal
data and password hashes: keep it out of git (backups/ is git-ignored) and delete it when no
longer needed.
"""

from __future__ import annotations

import base64
import json
import sqlite3
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import Connection, Table, create_engine, false, func, insert, make_url, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.pool import NullPool
from sqlmodel import Session, SQLModel, select

from app.services.clock import now_utc


def _plain(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"base64": base64.b64encode(value).decode("ascii")}
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def export_all(
    session: Session, out_dir: Path, *, with_evidence: bool = True
) -> tuple[Path, dict[str, int]]:
    tables: dict[str, list[dict[str, Any]]] = {}
    for table in SQLModel.metadata.sorted_tables:  # parents before children
        columns = [
            c
            for c in table.columns
            if with_evidence or not (table.name == "evidence" and c.name == "content")
        ]
        rows = session.exec(select(*columns)).mappings().all()  # type: ignore[call-overload]
        tables[table.name] = [{k: _plain(v) for k, v in row.items()} for row in rows]
    created = now_utc()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"risktrack-backup-{created:%Y%m%d-%H%M%S}.json"
    payload = {
        "created_at_utc": created.isoformat(),
        "with_evidence": with_evidence,
        "tables": tables,
    }
    path.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    return path, {name: len(rows) for name, rows in tables.items()}


# ── Remote backup database (PostgreSQL copy of the live SQLite database) ──────────────────────
#
# SQLite on the VPS is the live database. A PostgreSQL database (Neon) keeps a full, queryable
# copy, refreshed after each daily file backup, from which a new SQLite file can be rebuilt.


class BackupError(RuntimeError):
    """The copy was refused or did not match; the target was left as it was (one transaction)."""


@dataclass
class CopyReport:
    revision: str
    rows: dict[str, int]
    audit_entries: int

    @property
    def total(self) -> int:
        return sum(self.rows.values())


def _revision(conn: Connection) -> str | None:
    try:
        return conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    except DBAPIError:
        return None


def _schema_version(url: str) -> str | None:
    engine = create_engine(url, poolclass=NullPool)
    try:
        with engine.connect() as conn:
            return _revision(conn)
    finally:
        engine.dispose()


@contextmanager
def _snapshot(url: str) -> Iterator[str]:
    """A consistent point-in-time copy of a SQLite source (online backup API, safe while the app
    writes); other sources are read as they are, inside one transaction."""
    if not url.startswith("sqlite"):
        yield url
        return
    path = make_url(url).database
    if not path or path == ":memory:" or not Path(path).is_file():
        raise BackupError(f"SQLite source file not found: {path}")
    with tempfile.TemporaryDirectory(prefix="risktrack-snapshot-") as folder:
        copy = Path(folder) / "snapshot.sqlite3"
        source, target = sqlite3.connect(path), sqlite3.connect(copy)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        yield f"sqlite:///{copy}"


def _empty_target(dst: Connection, tables: list[Table], *, new_file: bool) -> None:
    if dst.dialect.name == "postgresql":
        quote = dst.dialect.identifier_preparer.quote
        names = ", ".join(quote(t.name) for t in tables)
        dst.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))
        return
    if not new_file:
        raise BackupError("The SQLite target already has a schema: restore into a new file.")
    for table in reversed(tables):  # rows the migrations created (default settings)
        if dst.execute(select(func.count()).select_from(table)).scalar():
            dst.execute(table.delete())


def _copy_rows(src: Connection, dst: Connection, table: Table, batch_size: int) -> int:
    result = src.execute(select(table)).mappings()
    count = 0
    while chunk := [dict(row) for row in result.fetchmany(batch_size)]:
        dst.execute(insert(table), chunk)
        count += len(chunk)
    return count


def _reset_sequences(dst: Connection, tables: list[Table]) -> None:
    """After explicit ids are inserted, the next generated id must follow the highest one."""
    if dst.dialect.name != "postgresql":
        return
    for table in tables:
        if "id" in table.c and table.c.id.primary_key:
            next_id = func.coalesce(func.max(table.c.id), 0) + 1
            sequence = func.pg_get_serial_sequence(table.name, "id")
            dst.execute(select(func.setval(sequence, next_id, false())).select_from(table))


def copy_database(source_url: str, target_url: str, *, batch_size: int = 500) -> CopyReport:
    """Copy every table from source to target, replacing what the target held.

    The target is first migrated to the latest schema; both sides must then be at the same
    revision. A PostgreSQL target is emptied with TRUNCATE (the insert-only triggers guard rows
    against UPDATE and DELETE, not a deliberate whole-table refresh); a SQLite target must be
    empty (a new file), so a restore never mixes old and new rows. Everything happens in one
    target transaction, and row counts and the audit hash chain are checked before returning.
    """
    import app.models  # noqa: F401  (registers every table on the metadata)
    from app.migrations import upgrade
    from app.services.audit import verify_chain

    if make_url(source_url) == make_url(target_url):
        raise BackupError("Source and target are the same database.")
    new_file = _schema_version(target_url) is None
    upgrade(target_url)
    tables = list(SQLModel.metadata.sorted_tables)  # parents before children
    with _snapshot(source_url) as snapshot_url:
        source = create_engine(snapshot_url, poolclass=NullPool)
        target = create_engine(target_url, poolclass=NullPool)
        try:
            with source.connect() as src, target.begin() as dst:
                revision, at_target = _revision(src), _revision(dst)
                if revision is None or revision != at_target:
                    raise BackupError(
                        f"Schema versions differ (source {revision}, target {at_target}): "
                        "migrate the source first."
                    )
                _empty_target(dst, tables, new_file=new_file)
                rows = {t.name: _copy_rows(src, dst, t, batch_size) for t in tables}
                _reset_sequences(dst, tables)
                for table in tables:
                    held = dst.execute(select(func.count()).select_from(table)).scalar()
                    if held != rows[table.name]:
                        raise BackupError(f"{table.name}: copied {rows[table.name]}, holds {held}.")
            with Session(target) as session:
                chain = verify_chain(session)
            if not chain.ok:
                raise BackupError(
                    f"Audit chain broken in the copy at entry {chain.first_broken_id}."
                )
        finally:
            source.dispose()
            target.dispose()
    return CopyReport(revision=revision, rows=rows, audit_entries=chain.entries_checked)
