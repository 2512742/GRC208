"""Database engine and session handling.

- SQLite (default): one file, foreign keys switched on for every connection.
- PostgreSQL on Neon from Vercel: no connection pool inside the function (NullPool), because frozen
  serverless instances must not hold connections; Neon's pooler does the pooling. Its pooler runs
  in transaction mode, which breaks server-side prepared statements, so psycopg's automatic
  preparation is turned off for pooled URLs.
"""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, event, make_url
from sqlalchemy.pool import NullPool
from sqlmodel import Session, create_engine

from app.core.config import Settings, get_settings


def build_engine(settings: Settings) -> Engine:
    kwargs: dict[str, Any] = {"echo": False}
    connect_args: dict[str, Any] = {}

    if settings.is_sqlite:
        connect_args["check_same_thread"] = False  # FastAPI may use the connection in a threadpool
        _ensure_sqlite_folder(settings.database_url)
    else:
        if settings.uses_connection_pooler:
            connect_args["prepare_threshold"] = None
        if settings.is_serverless:
            kwargs["poolclass"] = NullPool
        else:
            kwargs["pool_pre_ping"] = True  # Neon computes scale to zero; drop dead connections

    engine = create_engine(settings.database_url, connect_args=connect_args, **kwargs)

    if settings.is_sqlite:

        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_connection: Any, _record: Any) -> None:
            # Python's sqlite3 driver delays BEGIN until the first write, which makes SAVEPOINTs
            # start (and RELEASE commit) their own transactions. Take over transaction control
            # so SQLite transactions and savepoints behave like PostgreSQL's (SQLAlchemy recipe:
            # "Serializable isolation / Savepoints / Transactional DDL").
            dbapi_connection.isolation_level = None
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        @event.listens_for(engine, "begin")
        def _sqlite_begin(connection: Any) -> None:
            connection.exec_driver_sql("BEGIN")

    return engine


def _ensure_sqlite_folder(url: str) -> None:
    """SQLite creates the file but not its folder (e.g. a fresh clone without backend/data/)."""
    database = make_url(url).database
    if database and database != ":memory:":
        Path(database).parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_engine() -> Engine:
    return build_engine(get_settings())


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed."""
    with Session(get_engine()) as session:
        yield session
