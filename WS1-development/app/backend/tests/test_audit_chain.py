"""P2 audit chain: entries link up, verification passes, and tampering is detected (T22).

Tampering is simulated the way a database owner could do it: switch off the insert-only trigger
inside the test's transaction (rolled back afterwards on both PostgreSQL and SQLite), then edit.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import text
from sqlmodel import Session, col, select

from app.models import AuditLog
from app.models.enums import AuditAction
from app.models.records import GENESIS_HASH
from app.services import clock
from app.services.audit import AuditActor, compute_hash, record, verify_chain

OMOTAYO = AuditActor(user_id=None, username="omotayo", role="analyst", ip="102.89.1.10")


def _entries(db: Session) -> list[AuditLog]:
    return list(db.exec(select(AuditLog).order_by(col(AuditLog.id))))


def _bypass_trigger(db: Session) -> None:
    """What a database owner could do. Transactional on both databases, so it is undone."""
    if db.get_bind().dialect.name == "postgresql":
        db.exec(text("ALTER TABLE audit_log DISABLE TRIGGER trg_audit_log_insert_only"))  # type: ignore[call-overload]
    else:
        db.exec(text("DROP TRIGGER trg_audit_log_no_update"))  # type: ignore[call-overload]
        db.exec(text("DROP TRIGGER trg_audit_log_no_delete"))  # type: ignore[call-overload]


def test_entries_chain_from_genesis_and_verify(db: Session) -> None:
    first = record(
        db,
        AuditAction.CREATE,
        OMOTAYO,
        object_type="risk",
        object_id=1,
        after={"title": "Ledger race condition", "score": 20},
    )
    second = record(db, AuditAction.ASSESS, OMOTAYO, object_type="risk", object_id=1)
    assert first.prev_hash == GENESIS_HASH  # each test starts with an empty, rolled-back log
    assert second.prev_hash == first.hash
    assert first.hash == compute_hash(first)
    report = verify_chain(db)
    assert report.ok and report.entries_checked >= 2


def test_snapshot_of_who_and_values_normalised(db: Session) -> None:
    entry = record(
        db,
        AuditAction.UPDATE,
        OMOTAYO,
        object_type="action",
        object_id=7,
        before={"due": date(2026, 12, 5), "cost": Decimal("1500000.00")},
        after={"due": date(2026, 12, 20), "cost": Decimal("1750000.50")},
        detail="x" * 900,
    )
    db.expire(entry)
    stored = db.get(AuditLog, entry.id)
    assert stored is not None
    assert (stored.username, stored.role, stored.ip) == ("omotayo", "analyst", "102.89.1.10")
    assert stored.object_id == "7"
    assert stored.after == {"cost": "1750000.50", "due": "2026-12-20"}
    assert stored.detail is not None and len(stored.detail) == 500
    assert compute_hash(stored) == stored.hash  # survives the database round trip


def test_entry_time_comes_from_the_clock(db: Session) -> None:
    moment = datetime(2026, 12, 5, 20, 30, 15, 123456, tzinfo=UTC)
    with clock.frozen(moment):
        entry = record(db, AuditAction.LOGIN, OMOTAYO)
    db.expire(entry)
    assert db.get(AuditLog, entry.id).occurred_at == moment  # type: ignore[union-attr]
    assert verify_chain(db).ok


def test_t22_edited_content_is_detected(db: Session) -> None:
    record(db, AuditAction.CREATE, OMOTAYO, object_type="risk", object_id=1)
    victim = record(
        db,
        AuditAction.APPROVE,
        OMOTAYO,
        object_type="acceptance",
        object_id=3,
        after={"decided_by": "kelechi"},
    )
    record(db, AuditAction.EXPORT, OMOTAYO)
    _bypass_trigger(db)
    tampered = db.get(AuditLog, victim.id)
    assert tampered is not None
    tampered.after = {"decided_by": "emmanuel"}  # edited, hash left as it was
    db.flush()
    db.expire_all()
    report = verify_chain(db)
    assert not report.ok
    assert report.first_broken_id == victim.id
    assert report.problem == "entry content does not match its hash"


def test_t22_deleted_entry_is_detected(db: Session) -> None:
    record(db, AuditAction.CREATE, OMOTAYO)
    middle = record(db, AuditAction.DENIED, OMOTAYO, detail="tried to approve own risk")
    after = record(db, AuditAction.LOGOUT, OMOTAYO)
    _bypass_trigger(db)
    db.exec(text("DELETE FROM audit_log WHERE id = :id").bindparams(id=middle.id))  # type: ignore[call-overload]
    db.expire_all()
    report = verify_chain(db)
    assert not report.ok
    assert report.first_broken_id == after.id
    assert report.problem == "link to the previous entry is broken"


def test_t22_rehashed_forgery_still_breaks_the_next_link(db: Session) -> None:
    """Editing a row AND recomputing its hash still breaks the following entry's link."""
    record(db, AuditAction.CREATE, OMOTAYO)
    victim = record(db, AuditAction.APPROVE, OMOTAYO, after={"ok": True})
    follower = record(db, AuditAction.EXPORT, OMOTAYO)
    _bypass_trigger(db)
    forged = db.get(AuditLog, victim.id)
    assert forged is not None
    forged.after = {"ok": False}
    forged.hash = compute_hash(forged)
    db.flush()
    db.expire_all()
    report = verify_chain(db)
    assert not report.ok and report.first_broken_id == follower.id


def test_empty_log_verifies(db: Session) -> None:
    if not _entries(db):
        assert verify_chain(db).ok
