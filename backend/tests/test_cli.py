"""CLI: targets are described without credentials; load-reference works end to end."""

from __future__ import annotations

from sqlalchemy import Engine
from typer.testing import CliRunner

from app.cli import cli, describe_database


def test_describe_database_never_shows_credentials() -> None:
    url = "postgresql+psycopg://neondb_owner:s3cr3t@ep-x-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"
    text = describe_database(url)
    assert text == "PostgreSQL ep-x-pooler.us-east-2.aws.neon.tech/neondb"
    assert "s3cr3t" not in text and "neondb_owner" not in text


def test_load_reference_command(migrated_engine: Engine) -> None:
    result = CliRunner().invoke(cli, ["load-reference", "--yes"])
    assert result.exit_code == 0, result.output
    assert "Target database: SQLite file" in result.output or "PostgreSQL" in result.output
    assert "added" in result.output
