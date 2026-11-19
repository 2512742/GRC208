"""Hash-chained, append-only audit log (brief feature 7; PLAN.md decision 7).

Each entry's `hash` is the SHA-256 of a canonical JSON form of its own fields plus the previous
entry's hash. Changing, removing or reordering any past entry breaks every hash after it, and
`verify_chain` reports the first broken entry (test T22).

Concurrency: writers are serialised so two requests never extend the chain from the same entry
(PostgreSQL: a transaction-scoped advisory lock; SQLite: one writer at a time by design). The
unique `prev_hash` column is the last line of defence; a collision is retried.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from app.models import AuditLog
from app.models.enums import AuditAction
from app.models.records import GENESIS_HASH
from app.services.clock import now_utc

# Arbitrary constant naming the lock; any 64-bit integer works as long as it's used only here.
AUDIT_LOCK_KEY = 0x52_49_53_4B_41_55_44  # "RISKAUD"
MAX_APPEND_ATTEMPTS = 3
HASHED_FIELDS = (
    "occurred_at",
    "user_id",
    "username",
    "role",
    "action",
    "object_type",
    "object_id",
    "before",
    "after",
    "detail",
    "ip",
    "prev_hash",
)


def jsonable(value: Any) -> Any:
    """Normalise to plain JSON types (dates, decimals and enums become strings), so the stored
    value and the hashed value are identical after a database round trip."""
    if value is None:
        return None
    return json.loads(json.dumps(value, default=str, sort_keys=True))


def _canonical_time(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat(timespec="microseconds")


def compute_hash(entry: AuditLog) -> str:
    payload = {name: getattr(entry, name) for name in HASHED_FIELDS}
    payload["occurred_at"] = _canonical_time(entry.occurred_at)
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AuditActor:
    """Who acted. Username and role are copied into the entry, so the log still reads correctly
    after a user is renamed or changes role."""

    user_id: int | None
    username: str | None
    role: str | None
    ip: str | None = None


SYSTEM = AuditActor(user_id=None, username="system", role=None)


def _lock_chain(session: Session) -> None:
    if session.get_bind().dialect.name == "postgresql":
        session.exec(text("SELECT pg_advisory_xact_lock(:key)").bindparams(key=AUDIT_LOCK_KEY))  # type: ignore[call-overload]


def _last_hash(session: Session) -> str:
    last = session.exec(select(AuditLog.hash).order_by(col(AuditLog.id).desc()).limit(1)).first()
    return last or GENESIS_HASH


def record(
    session: Session,
    action: AuditAction,
    actor: AuditActor = SYSTEM,
    *,
    object_type: str | None = None,
    object_id: str | int | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    detail: str | None = None,
) -> AuditLog:
    """Append one entry in the caller's transaction (it commits or rolls back with the change
    it describes, so the log never claims something that didn't happen)."""
    for attempt in range(1, MAX_APPEND_ATTEMPTS + 1):
        savepoint = session.begin_nested()
        try:
            _lock_chain(session)
            entry = AuditLog(
                occurred_at=now_utc(),
                user_id=actor.user_id,
                username=actor.username,
                role=actor.role,
                action=AuditAction(action).value,
                object_type=object_type,
                object_id=None if object_id is None else str(object_id),
                before=jsonable(before),
                after=jsonable(after),
                detail=detail[:500] if detail else None,
                ip=actor.ip,
                prev_hash=_last_hash(session),
                hash="",
            )
            entry.hash = compute_hash(entry)
            session.add(entry)
            session.flush()
            savepoint.commit()
            return entry
        except IntegrityError:
            savepoint.rollback()
            if attempt == MAX_APPEND_ATTEMPTS:
                raise
    raise AssertionError("unreachable")  # pragma: no cover


@dataclass(frozen=True)
class ChainReport:
    ok: bool
    entries_checked: int
    first_broken_id: int | None = None
    problem: str | None = None


def verify_chain(session: Session) -> ChainReport:
    """Walk the whole log in order and recompute every link."""
    expected_prev = GENESIS_HASH
    checked = 0
    rows = session.exec(
        select(AuditLog).order_by(col(AuditLog.id)).execution_options(yield_per=500)
    )
    for entry in rows:
        checked += 1
        if entry.prev_hash != expected_prev:
            return ChainReport(False, checked, entry.id, "link to the previous entry is broken")
        if compute_hash(entry) != entry.hash:
            return ChainReport(False, checked, entry.id, "entry content does not match its hash")
        expected_prev = entry.hash
    return ChainReport(True, checked)
