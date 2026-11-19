"""Command-line tools:  python -m app.cli --help   (run from app/backend)

Every command states which database it is about to touch, so a Neon URL in `.env` is never
changed by surprise. Commands: load-reference, create-user, seed-demo, verify-audit, export-backup.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

import typer
from sqlmodel import Session

from app.core.config import get_settings
from app.db import get_engine
from app.models.enums import Role

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


@cli.command("create-user")
def create_user_command(
    username: str = typer.Option(..., help="Login name (lowercase letters, digits, . _ -)"),
    full_name: str = typer.Option(..., "--full-name"),
    role: Role = typer.Option(..., case_sensitive=False),
    email: str | None = typer.Option(None),
    job_title: str | None = typer.Option(None, "--job-title"),
    department: str | None = typer.Option(None),
    password: str = typer.Option(
        ...,
        prompt=True,
        hide_input=True,
        confirmation_prompt=True,
        help="Prompted for (hidden) if not given",
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Don't ask before touching a remote DB"),
) -> None:
    """Create a user (the first admin is created this way)."""
    from app.services.users import UserError, create_user

    confirm_target(get_settings().database_url, yes)
    with Session(get_engine()) as session:
        try:
            user = create_user(
                session,
                username=username,
                full_name=full_name,
                role=role,
                password=password,
                email=email,
                job_title=job_title,
                department=department,
            )
        except UserError as exc:
            typer.echo(f"Not created: {exc}", err=True)
            raise typer.Exit(code=1) from exc
        session.commit()
        typer.echo(f"Created {user.username} ({user.role}), id {user.id}")


# Local-only convenience: documented in the README, never used for a remote database.
LOCAL_DEMO_PASSWORD = "Alajo-Demo-2026!"  # noqa: S105  (local SQLite demo only)


@cli.command("seed-demo")
def seed_demo_command(
    reset: bool = typer.Option(
        False, "--reset", help="ERASE all data and rebuild the schema first"
    ),
    password: str | None = typer.Option(
        None, envvar="DEMO_PASSWORD", help="Password for every demo account (asked if remote)"
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Don't ask before touching a remote DB"),
) -> None:
    """Load The Alajo demo data (people, services, assets, scored risks)."""
    from app.migrations import reset as reset_schema
    from app.services.demo_seed import SeedError, seed_demo

    settings = get_settings()
    remote = not settings.is_sqlite
    confirm_target(settings.database_url, yes)
    if reset and remote and not yes:
        typer.confirm(
            "--reset ERASES every record in this remote database. Really continue?", abort=True
        )
    if password is None:
        password = (
            typer.prompt("Demo account password", hide_input=True, confirmation_prompt=True)
            if remote
            else LOCAL_DEMO_PASSWORD
        )
    if reset:
        reset_schema(settings.migration_database_url)
        typer.echo("Schema rebuilt.")
    with Session(get_engine()) as session:
        try:
            report = seed_demo(session, password)
        except SeedError as exc:
            typer.echo(f"Seed failed: {exc}", err=True)
            raise typer.Exit(code=1) from exc
        session.commit()
    typer.echo(
        f"Seeded {report.users} users, {report.services} services, {report.assets} assets, "
        f"{report.risks} risks ({report.assessed} assessed, {report.above_appetite} above "
        f"appetite); {report.decisions} decisions, {report.actions} actions "
        f"({report.completed} completed), {report.reassessed} reassessed, "
        f"{report.acceptances} acceptance requests, {report.evidence} evidence files; "
        f"{report.reference_added} reference rows added."
    )


@cli.command("verify-audit")
def verify_audit_command() -> None:
    """Recompute the audit log's hash chain; exit code 1 if it is broken."""
    from app.services.audit import verify_chain

    typer.echo(f"Target database: {describe_database(get_settings().database_url)}")
    with Session(get_engine()) as session:
        report = verify_chain(session)
    if report.ok:
        typer.echo(f"OK: {report.entries_checked} entries, chain intact.")
        return
    typer.echo(
        f"BROKEN at entry {report.first_broken_id}: {report.problem} "
        f"({report.entries_checked} entries checked).",
        err=True,
    )
    raise typer.Exit(code=1)


@cli.command("export-backup")
def export_backup_command(
    out_dir: Path = typer.Option(Path("backups"), "--out", help="Folder for the JSON file"),
    with_evidence: bool = typer.Option(True, help="Include evidence file contents (base64)"),
) -> None:
    """Write every table to one JSON file (database-version independent, like Django's dumpdata
    in the Guardian runbook). Run it before any schema change or database move."""
    from app.services.backup import export_all

    typer.echo(f"Source database: {describe_database(get_settings().database_url)}")
    with Session(get_engine()) as session:
        path, counts = export_all(session, out_dir, with_evidence=with_evidence)
    typer.echo(f"Wrote {path} ({sum(counts.values())} rows in {len(counts)} tables).")


if __name__ == "__main__":
    cli()
