"""Load the reference catalogue (controls, obligations) into the database.

Idempotent: adds missing entries, updates changed titles, never deletes (rows may be linked to
actions, assets or risks). Called by `python -m app.cli load-reference` and by `seed-demo`.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlmodel import Session, select

from app.models import Control, Obligation
from app.reference.catalogue import CONTROLS, OBLIGATIONS, TO_VERIFY


@dataclass(frozen=True)
class LoadResult:
    added: int
    updated: int
    unchanged: int


def load_reference_data(session: Session) -> LoadResult:
    added = updated = unchanged = 0

    existing_controls = {(c.framework, c.control_ref): c for c in session.exec(select(Control))}
    for framework, ref, title in CONTROLS:
        row = existing_controls.get((framework.value, ref))
        if row is None:
            session.add(Control(framework=framework.value, control_ref=ref, short_title=title))
            added += 1
        elif row.short_title != title:
            row.short_title = title
            updated += 1
        else:
            unchanged += 1

    existing_obligations = {(o.regime, o.reference): o for o in session.exec(select(Obligation))}
    for regime, ref, title in OBLIGATIONS:
        row = existing_obligations.get((regime.value, ref))
        if row is None:
            session.add(
                Obligation(
                    regime=regime.value, reference=ref, short_title=title, source_note=TO_VERIFY
                )
            )
            added += 1
        elif row.short_title != title:
            row.short_title = title
            updated += 1
        else:
            unchanged += 1

    session.commit()
    return LoadResult(added=added, updated=updated, unchanged=unchanged)
