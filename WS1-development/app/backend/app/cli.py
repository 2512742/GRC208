"""Command-line tools:  python -m app.cli --help   (run from app/backend)

Every command states which database it is about to touch, so a Neon URL in `.env` is never
changed by surprise. Commands: load-reference, create-user, seed-demo, verify-audit, export-backup,
backup-to-postgres, restore-from-backup.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

import typer
from sqlmodel import Session

from app.core.config import get_settings
from app.db import get_engine
from app.models.enums import Role

# Never show local variables in error output: they can hold database URLs with passwords.
cli = typer.Typer(
    no_args_is_help=True,
    help="RiskTrack management commands",
    pretty_exceptions_show_locals=False,
)


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


@cli.command("reset-password")
def reset_password_command(
    username: str = typer.Option(..., help="The account to recover"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Don't ask before touching a remote DB"),
) -> None:
    """Offline recovery (e.g. a lost admin password): sets a one-off temporary password that must
    be changed at the next sign-in, ends the account's sessions, and unlocks nothing else.
    Needs shell access to the server and its .env, which is the proof of authority."""
    from sqlmodel import func, select

    from app.models import User
    from app.models.enums import AuditAction
    from app.services import account, audit

    confirm_target(get_settings().database_url, yes)
    with Session(get_engine()) as session:
        user = session.exec(
            select(User).where(func.lower(User.username) == username.strip().lower())
        ).first()
        if user is None:
            typer.echo(f"No user '{username}'.", err=True)
            raise typer.Exit(code=1)
        temporary = account.temporary_password()
        account.set_password(session, user, temporary, must_change=True)
        ended = account.revoke_sessions(session, user.id or 0)
        audit.record(
            session,
            AuditAction.UPDATE,
            audit.SYSTEM,
            object_type="user",
            object_id=user.id,
            detail=f"password reset from the command line; {ended} session(s) ended",
        )
        name, active = user.username, user.is_active
        session.commit()
    typer.echo(f"Temporary password for {name}: {temporary}")
    typer.echo("It must be changed at the next sign-in. Share it privately, never in chat.")
    if not active:
        typer.echo("Note: this account is disabled; an administrator must enable it first.")


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


@cli.command("export-openapi")
def export_openapi_command(
    out: Path = typer.Option(Path("openapi.json"), help="Where to write the API contract"),
) -> None:
    """Write the OpenAPI contract the frontend generates its types from (npm run gen:api)."""
    import json

    from app.main import app

    out.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    typer.echo(f"Wrote {out}")


def _backup_url() -> str:
    url = get_settings().backup_database_url
    if not url:
        typer.echo("BACKUP_DATABASE_URL is not set (the remote PostgreSQL backup).", err=True)
        raise typer.Exit(code=2)
    return url


@cli.command("backup-to-postgres")
def backup_to_postgres_command(
    yes: bool = typer.Option(False, "--yes", "-y", help="Don't ask before replacing the copy"),
) -> None:
    """Replace the remote PostgreSQL backup with a full copy of the live database."""
    from app.services.backup import BackupError, copy_database

    settings = get_settings()
    target = _backup_url()
    typer.echo(f"From: {describe_database(settings.database_url)}")
    typer.echo(f"To:   {describe_database(target)} (its current contents are replaced)")
    if not yes:
        typer.confirm("Continue?", abort=True)
    try:
        report = copy_database(settings.database_url, target)
    except BackupError as exc:
        typer.echo(f"Backup failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(
        f"OK: {report.total} rows in {len(report.rows)} tables at revision {report.revision}; "
        f"audit chain intact ({report.audit_entries} entries)."
    )


@cli.command("restore-from-backup")
def restore_from_backup_command(
    into: Path = typer.Option(..., "--into", help="New SQLite file to create (must not exist)"),
) -> None:
    """Rebuild a SQLite database from the remote PostgreSQL backup, into a new file."""
    from app.services.backup import BackupError, copy_database

    source = _backup_url()
    into = into.resolve()
    if into.exists():
        typer.echo(f"{into} already exists; choose a new file name.", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"From: {describe_database(source)}")
    typer.echo(f"To:   new SQLite file {into}")
    try:
        report = copy_database(source, f"sqlite:///{into}")
    except BackupError as exc:
        into.unlink(missing_ok=True)
        typer.echo(f"Restore failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(
        f"OK: {report.total} rows restored; audit chain intact ({report.audit_entries} entries). "
        "Stop the app, replace the live file with this one, then start it again."
    )


if __name__ == "__main__":
    cli()
