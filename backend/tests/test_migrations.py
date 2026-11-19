"""P1: the Alembic baseline builds the schema, round-trips, and matches the models exactly."""

from __future__ import annotations

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, inspect, text
from sqlmodel import SQLModel

from app.models import INSERT_ONLY_TABLES
from tests.conftest import alembic_config


def test_upgrade_creates_every_model_table(migrated_engine: Engine) -> None:
    tables = set(inspect(migrated_engine).get_table_names())
    assert set(SQLModel.metadata.tables) <= tables
    assert "alembic_version" in tables


def test_database_is_at_the_single_head(migrated_engine: Engine) -> None:
    heads = ScriptDirectory.from_config(alembic_config(str(migrated_engine.url))).get_heads()
    assert len(heads) == 1, "migration history must not branch"
    with migrated_engine.connect() as conn:
        current = MigrationContext.configure(conn).get_current_revision()
    assert current == heads[0]


def test_models_and_migrations_do_not_drift(migrated_engine: Engine) -> None:
    """If this fails, a model changed without a migration: run `alembic revision --autogenerate`."""
    with migrated_engine.connect() as conn:
        diff = compare_metadata(
            MigrationContext.configure(conn, opts={"compare_type": True}), SQLModel.metadata
        )
    assert diff == []


def test_settings_row_has_methodology_defaults(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as conn:
        row = conn.execute(text("SELECT * FROM app_setting")).mappings().all()
    assert len(row) == 1
    s = row[0]
    assert s["id"] == 1
    assert s["appetite_threshold"] == 10
    assert (s["sla_days_critical"], s["sla_days_high"], s["sla_days_medium"]) == (30, 90, 180)
    assert (s["review_days_critical"], s["review_days_high"]) == (30, 90)
    assert (s["review_days_medium"], s["review_days_low"]) == (180, 365)
    assert s["org_timezone"] == "Africa/Lagos"


def test_insert_only_triggers_exist(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as conn:
        if conn.dialect.name == "postgresql":
            rows = conn.execute(
                text("SELECT event_object_table FROM information_schema.triggers")
            ).scalars()
        else:
            rows = conn.execute(
                text("SELECT tbl_name FROM sqlite_master WHERE type = 'trigger'")
            ).scalars()
        protected = set(rows)
    assert set(INSERT_ONLY_TABLES) <= protected


def test_downgrade_to_base_and_back(migrated_engine: Engine) -> None:
    """Runs last in this module on purpose: it rebuilds the schema the other tests use."""
    cfg = alembic_config(str(migrated_engine.url.render_as_string(hide_password=False)))
    command.downgrade(cfg, "base")
    assert set(inspect(migrated_engine).get_table_names()) <= {"alembic_version"}
    command.upgrade(cfg, "head")
    assert set(SQLModel.metadata.tables) <= set(inspect(migrated_engine).get_table_names())
