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
from typing import Any

from sqlalchemy import Engine, event
from sqlalchemy.pool import NullPool
from sqlmodel import Session, create_engine

from app.core.config import Settings, get_settings


def build_engine(settings: Settings) -> Engine:
    kwargs: dict[str, Any] = {"echo": False}
    connect_args: dict[str, Any] = {}

    if settings.is_sqlite:
        connect_args["check_same_thread"] = False  # FastAPI may use the connection in a threadpool
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
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


@lru_cache
def get_engine() -> Engine:
    return build_engine(get_settings())


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed."""
    with Session(get_engine()) as session:
        yield session
