"""P1: reference catalogue loads once and reloads idempotently."""

from __future__ import annotations

from sqlmodel import Session, func, select

from app.models import Control, Obligation
from app.models.enums import Framework, Regime
from app.reference.catalogue import CONTROLS, OBLIGATIONS
from app.services.reference_data import load_reference_data


def test_catalogue_has_no_duplicates() -> None:
    assert len({(f, ref) for f, ref, _ in CONTROLS}) == len(CONTROLS)
    assert len({(r, ref) for r, ref, _ in OBLIGATIONS}) == len(OBLIGATIONS)


def test_catalogue_covers_every_framework_and_regime() -> None:
    assert {f for f, _, _ in CONTROLS} == set(Framework)
    assert {r for r, _, _ in OBLIGATIONS} == set(Regime)


def test_load_is_idempotent(db: Session) -> None:
    first = load_reference_data(db)  # other tests may have loaded some rows already
    assert first.added + first.updated + first.unchanged == len(CONTROLS) + len(OBLIGATIONS)
    second = load_reference_data(db)
    assert (second.added, second.updated) == (0, 0)
    assert db.exec(select(func.count()).select_from(Control)).one() == len(CONTROLS)
    assert db.exec(select(func.count()).select_from(Obligation)).one() == len(OBLIGATIONS)


def test_changed_titles_are_updated_not_duplicated(db: Session) -> None:
    load_reference_data(db)
    row = db.exec(select(Control).where(Control.control_ref == "ID.RA")).one()
    row.short_title = "old wording"
    db.flush()
    result = load_reference_data(db)
    assert result.updated == 1
    db.refresh(row)
    assert row.short_title == "Risk assessment"


def test_obligations_flagged_for_source_verification(db: Session) -> None:
    load_reference_data(db)
    notes = set(db.exec(select(Obligation.source_note)))
    assert notes == {"Source clause to be confirmed by WS2 before citing"}
