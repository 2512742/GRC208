"""Command-line tools:  python -m app.cli --help   (run from app/backend)

Every command states which database it is about to touch, so a Neon URL in `.env` is never
changed by surprise. Later phases add: seed-demo, create-user, verify-audit, export-backup.
"""

from __future__ import annotations

from urllib.parse import urlsplit

import typer
from sqlmodel import Session

from app.core.config import get_settings
from app.db import get_engine

cli = typer.Typer(no_args_is_help=True, help="RiskTrack management commands")


@cli.callback()
def main() -> None:
    """RiskTrack management commands (run from app/backend)."""


def describe_database(url: str) -> str:
    """Human-readable target without credentials."""
    if url.startswith("sqlite"):
        return f"SQLite file {url.split(':///', 1)[-1]}"
    parts = urlsplit(url)
    return f"PostgreSQL {parts.hostname}/{parts.path.lstrip('/')}"


def confirm_target(url: str, assume_yes: bool) -> None:
    target = describe_database(url)
    typer.echo(f"Target database: {target}")
    if url.startswith("sqlite") or assume_yes:
        return
    typer.confirm("This is a remote database. Continue?", abort=True)


@cli.command("load-reference")
def load_reference(
    yes: bool = typer.Option(False, "--yes", "-y", help="Don't ask before touching a remote DB"),
) -> None:
    """Add or update framework controls and regulatory obligations (idempotent)."""
    from app.services.reference_data import load_reference_data

    confirm_target(get_settings().database_url, yes)
    with Session(get_engine()) as session:
        result = load_reference_data(session)
    typer.echo(f"added {result.added}, updated {result.updated}, unchanged {result.unchanged}")


if __name__ == "__main__":
    cli()
