"""P4 seed: the Alajo sample data loads, meets the brief's minimums and reproduces PLAN §4.2."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlmodel import Session, col, func, select

from app.models import Asset, AuditLog, BusinessService, Risk, RiskAssessment, User
from app.schemas.rows import AssetRow, RiskRow
from app.services.demo_seed import SAMPLE_DIR, SeedError, read_rows, seed_demo
from tests.conftest import DEMO_PASSWORD

# PLAN.md §4.2 starter register: code -> (likelihood, impact, owner username)
EXPECTED = {
    "R-001": (4, 5, "emmanuel"),
    "R-002": (4, 5, "emmanuel"),
    "R-003": (3, 5, "gilbert"),
    "R-004": (3, 5, "anita"),
    "R-005": (4, 4, "emmanuel"),
    "R-006": (3, 4, "anita"),
    "R-007": (4, 4, "gilbert"),
    "R-008": (2, 5, "emmanuel"),
    "R-009": (3, 4, "anita"),
    "R-010": (3, 3, "gilbert"),
    "R-011": (2, 4, "anita"),
    "R-012": (4, 4, "gilbert"),
    "R-013": (3, 4, "gilbert"),
    "R-014": (3, 4, "anita"),
    "R-015": (2, 5, "adeola"),
    "R-016": (3, 5, "emmanuel"),
    "R-017": (3, 3, "emmanuel"),
    "R-018": (3, 3, "gilbert"),
    "R-019": (2, 4, "gilbert"),
    "R-020": (4, 3, "gilbert"),
    "R-021": (2, 4, "emmanuel"),
    "R-022": (2, 3, "anita"),
}


def count(db: Session, model: type) -> int:
    return db.exec(select(func.count()).select_from(model)).one()


@pytest.fixture
def seeded(db: Session) -> Session:
    if count(db, Risk):
        pytest.skip("database already holds risks")
    seed_demo(db, DEMO_PASSWORD)
    return db


def test_sample_files_are_valid_import_rows() -> None:
    assert len(read_rows(SAMPLE_DIR / "alajo_assets.csv", AssetRow)) == 18
    assert len(read_rows(SAMPLE_DIR / "alajo_risks.csv", RiskRow)) == 22


def test_t30_part1_minimum_demonstration_data(seeded: Session) -> None:
    db = seeded
    assert count(db, BusinessService) == 3
    assert count(db, Asset) >= 15
    per_service = dict(
        db.exec(select(Asset.service_id, func.count()).group_by(Asset.service_id)).all()
    )
    assert len(per_service) == 3 and all(n >= 5 for n in per_service.values())
    assert count(db, Risk) >= 20
    above = db.exec(
        select(func.count())
        .select_from(RiskAssessment)
        .where(col(RiskAssessment.above_appetite).is_(True))
    ).one()
    assert above >= 1


def test_register_matches_plan_4_2(seeded: Session) -> None:
    db = seeded
    rows = db.exec(
        select(Risk.risk_code, RiskAssessment.likelihood, RiskAssessment.impact, User.username)
        .join(RiskAssessment, RiskAssessment.risk_id == Risk.id)
        .join(User, User.id == Risk.owner_id)
    ).all()
    assert {code: (lk, im, who) for code, lk, im, who in rows} == EXPECTED


def test_every_seeded_record_is_audited_as_the_analyst(seeded: Session) -> None:
    db = seeded
    creators = set(
        db.exec(
            select(AuditLog.username).where(
                AuditLog.object_type.in_(  # type: ignore[attr-defined]
                    ["service", "asset", "risk"]
                )
            )
        )
    )
    assert creators == {"omotayo"}
    from app.services.audit import verify_chain

    assert verify_chain(db).ok


def test_personas_have_their_roles(seeded: Session) -> None:
    roles = dict(seeded.exec(select(User.username, User.role)).all())
    assert roles["adeola"] == roles["kelechi"] == "approver"
    assert roles["ernestina"] == "auditor" and roles["omotayo"] == "analyst"


def test_seed_refuses_to_run_twice(seeded: Session) -> None:
    with pytest.raises(SeedError, match="already has risks"):
        seed_demo(seeded, DEMO_PASSWORD)


def test_invalid_sample_rows_are_reported_with_row_numbers(tmp_path: Path) -> None:
    bad = tmp_path / "alajo_risks.csv"
    bad.write_text(
        "risk_code,title,asset_codes,owner_username,likelihood,impact,threat,vulnerability,"
        "business_impact,rationale\n"
        "R-001,Valid title here,A-001,emmanuel,4,5,t,v,i,because\n"
        "R-002,Bad,,emmanuel,6,x,t,v,i,\n",
        encoding="utf-8",
    )
    with pytest.raises(SeedError) as info:
        read_rows(bad, RiskRow)
    message = str(info.value)
    assert "row 3" in message and "row 2" not in message
    assert "title" in message and "asset_codes" in message and "likelihood" in message
