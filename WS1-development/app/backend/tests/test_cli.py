"""CLI: targets are described without credentials; load-reference works end to end."""

from __future__ import annotations

import re

from sqlalchemy import Engine
from sqlmodel import Session, select
from typer.testing import CliRunner

from app.cli import cli, describe_database
from app.models import User


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


def test_create_user_command(migrated_engine: Engine) -> None:
    runner = CliRunner()
    args = [
        "create-user",
        "--username",
        "cli.admin",
        "--full-name",
        "CLI Admin",
        "--role",
        "admin",
        "--password",
        "Strong-Enough-123",
        "--yes",
    ]
    first = runner.invoke(cli, args)
    assert first.exit_code == 0, first.output
    assert "Created cli.admin (admin)" in first.output
    again = runner.invoke(cli, args)
    assert again.exit_code == 1 and "already taken" in again.output


def test_create_user_refuses_weak_password(migrated_engine: Engine) -> None:
    result = CliRunner().invoke(
        cli,
        [
            "create-user",
            "--username",
            "weak.user",
            "--full-name",
            "Weak User",
            "--role",
            "auditor",
            "--password",
            "short",
            "--yes",
        ],
    )
    assert result.exit_code == 1 and "at least 10 characters" in result.output


def test_reset_password_cli(migrated_engine: Engine) -> None:
    runner = CliRunner()
    made = runner.invoke(
        cli,
        [
            "create-user",
            "--username",
            "cli.reset",
            "--full-name",
            "CLI Reset",
            "--role",
            "admin",
            "--password",
            "Forgotten-Pass-99",
            "--yes",
        ],
    )
    assert made.exit_code == 0, made.output
    result = runner.invoke(cli, ["reset-password", "--username", "cli.reset", "--yes"])
    assert result.exit_code == 0, result.output
    temporary = re.search(r"Temporary password for cli\.reset: (\S+)", result.output)
    code_shape = r"[A-HJ-NP-Z2-9]{5}(-[A-HJ-NP-Z2-9]{5}){3}"
    assert temporary and re.fullmatch(code_shape, temporary.group(1))
    with Session(migrated_engine) as session:
        account = session.exec(select(User).where(User.username == "cli.reset")).one()
        assert account.must_change_password is True
    missing = runner.invoke(cli, ["reset-password", "--username", "ghost", "--yes"])
    assert missing.exit_code == 1
