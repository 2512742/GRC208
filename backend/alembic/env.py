"""Alembic environment.

The database URL comes from the app settings: DATABASE_URL_DIRECT if set (Neon's non-pooled
endpoint, required for migrations), otherwise DATABASE_URL. Nothing is hardcoded in alembic.ini.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

import app.models  # noqa: F401  registers every table on SQLModel.metadata
from app.core.config import get_settings
from app.models.base import UTCDateTime

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def _render_item(type_: str, obj: object, autogen_context: object) -> str | bool:
    """Render app-specific column types as plain SQLAlchemy types, so migrations never import
    application code that may change later."""
    if type_ == "type" and isinstance(obj, UTCDateTime):
        return "sa.DateTime(timezone=True)"
    return False


def _database_url() -> str:
    # An explicit URL (tests, CLI) wins over settings.
    return config.attributes.get("database_url") or get_settings().migration_database_url


def run_migrations_offline() -> None:
    url = _database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=url.startswith("sqlite"),
        compare_type=True,
        render_item=_render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = _database_url()
    connectable = config.attributes.get("connection")
    if connectable is None:
        connectable = engine_from_config(
            {"sqlalchemy.url": url}, prefix="sqlalchemy.", poolclass=pool.NullPool
        )
        with connectable.connect() as connection:
            _run(connection)
    else:
        _run(connectable)


def _run(connection) -> None:  # type: ignore[no-untyped-def]
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=connection.dialect.name == "sqlite",
        compare_type=True,
        render_item=_render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
