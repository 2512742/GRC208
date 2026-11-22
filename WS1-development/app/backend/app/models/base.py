"""Shared pieces for every table: constraint naming, UTC timestamps, CHECK helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Dialect
from sqlalchemy.types import TypeDecorator
from sqlmodel import SQLModel

# Predictable constraint names: needed for Alembic on SQLite (batch mode) and readable errors.
SQLModel.metadata.naming_convention = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class UTCDateTime(TypeDecorator[datetime]):
    """Timezone-aware UTC in and out, on PostgreSQL (timestamptz) and SQLite (text).

    Naive datetimes are refused, so a local time can never be stored by mistake.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime refused: pass a timezone-aware value")
        return value.astimezone(UTC)

    def process_result_value(self, value: Any, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:  # SQLite returns naive values; they were stored as UTC
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


def allowed(column: str, values: type[StrEnum], name: str | None = None) -> CheckConstraint:
    """CHECK (column IN (...)) built from a StrEnum, so code and database agree."""
    items = ", ".join(f"'{member.value}'" for member in values)
    return CheckConstraint(f"{column} IN ({items})", name=name or f"{column}_allowed")


def between(column: str, low: int, high: int, name: str | None = None) -> CheckConstraint:
    return CheckConstraint(f"{column} BETWEEN {low} AND {high}", name=name or f"{column}_range")
