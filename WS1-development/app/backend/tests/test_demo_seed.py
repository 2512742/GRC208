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
        .where(RiskAssessment.assessment_type == "initial")
        .join(User, User.id == Risk.owner_id)
    ).all()
    assert {code: (lk, im, who) for code, lk, im, who in rows} == EXPECTED


def test_every_seeded_record_is_audited_as_the_analyst(seeded: Session) -> None:
    db = seeded
    creators = set(
        db.exec(
            select(AuditLog.username)
            .where(AuditLog.action == "CREATE")
            .where(
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


def test_t30_part2_every_required_demo_state_present(seeded: Session) -> None:
    """Brief 'minimum demonstration data': >=12 actions, an overdue action, an expired
    acceptance, a completed treatment awaiting reassessment, risks above appetite."""
    from app.models import AcceptanceRequest, Evidence, TreatmentAction
    from app.services.governance import org_today
    from app.services.workflow import acceptance_is_expired, action_is_overdue

    db = seeded
    today = org_today(db)
    actions = db.exec(select(TreatmentAction)).all()
    assert len(actions) >= 12
    assert [a.action_code for a in actions if action_is_overdue(a.status, a.due_date, today)] == [
        "T-003"
    ]

    acceptances = db.exec(select(AcceptanceRequest)).all()
    expired = [a for a in acceptances if acceptance_is_expired(a.status, a.expiry_date, today)]
    assert len(expired) == 1
    assert {a.status for a in acceptances} == {"approved", "pending"}

    risks = {r.risk_code: r for r in db.exec(select(Risk))}
    assert risks["R-002"].status == "awaiting_reassessment"
    assert (
        db.exec(
            select(RiskAssessment.score)
            .where(RiskAssessment.risk_id == risks["R-002"].id)
            .order_by(col(RiskAssessment.id).desc())
        ).first()
        == 20
    )
    r013 = db.exec(
        select(RiskAssessment.score)
        .where(RiskAssessment.risk_id == risks["R-013"].id)
        .order_by(col(RiskAssessment.id))
    ).all()
    assert list(r013) == [12, 4]
    assert risks["R-010"].status == "accepted"
    completed = [a for a in actions if a.status == "completed"]
    assert {a.action_code for a in completed} == {"T-002", "T-011"}
    assert db.exec(select(func.count()).select_from(Evidence)).one() == 3


def test_ciso_owned_pending_request_only_the_cro_may_decide(seeded: Session) -> None:
    from app.core.permissions import Actor, Perm, Target, authorize
    from app.models import AcceptanceRequest
    from app.models.enums import Role

    db = seeded
    users = {u.username: u for u in db.exec(select(User))}
    r015 = db.exec(select(Risk).where(Risk.risk_code == "R-015")).one()
    request = db.exec(select(AcceptanceRequest).where(AcceptanceRequest.risk_id == r015.id)).one()
    target = Target(risk_owner_id=r015.owner_id, acceptance_requested_by_id=request.requested_by_id)
    assert not authorize(Actor(users["adeola"].id, Role.APPROVER), Perm.DECIDE_ACCEPTANCE, target)
    assert authorize(Actor(users["kelechi"].id, Role.APPROVER), Perm.DECIDE_ACCEPTANCE, target)


def test_seeded_audit_log_is_chronological(seeded: Session) -> None:
    first = seeded.connection().info["audit_before_seed"]
    times = list(
        seeded.exec(
            select(AuditLog.occurred_at).where(AuditLog.id > first).order_by(col(AuditLog.id))
        )
    )
    assert len(times) > 100
    assert times == sorted(times)
