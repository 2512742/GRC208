"""P1: rules the *database* enforces, independent of the API (defence in depth).

Basis for T02 (L/I range), T05-adjacent integrity, T11 (assessments can't be edited) and the
acceptance SoD rule that the requester can never decide their own request.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlmodel import Session, select

from app.models import (
    AcceptanceRequest,
    AppSetting,
    AuditLog,
    Evidence,
    TreatmentAction,
    TreatmentDecision,
)
from app.models.enums import Role
from app.models.records import EVIDENCE_MAX_BYTES, GENESIS_HASH
from tests.factories import (
    assessment,
    expect_db_error,
    future,
    make_asset,
    make_risk,
    make_service,
    make_user,
)

# ── Assessments ────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(("likelihood", "impact"), [(0, 3), (6, 3), (3, 0), (3, 6)])
def test_likelihood_and_impact_must_be_1_to_5(db: Session, likelihood: int, impact: int) -> None:
    analyst = make_user(db)
    risk = make_risk(db, analyst)
    row = assessment(risk, analyst, 3, 3)
    row.likelihood, row.impact, row.score = likelihood, impact, likelihood * impact
    with expect_db_error(db):
        db.add(row)


def test_score_must_equal_likelihood_times_impact(db: Session) -> None:
    analyst = make_user(db)
    risk = make_risk(db, analyst)
    with expect_db_error(db, "score_is_l_times_i"):
        db.add(assessment(risk, analyst, 4, 5, score=19))


@pytest.mark.parametrize(
    ("l_", "i", "wrong_band"), [(4, 5, "high"), (3, 3, "low"), (2, 2, "medium")]
)
def test_band_must_match_score(db: Session, l_: int, i: int, wrong_band: str) -> None:
    analyst = make_user(db)
    risk = make_risk(db, analyst)
    with expect_db_error(db, "band_matches_score"):
        db.add(assessment(risk, analyst, l_, i, band=wrong_band))


def test_appetite_flag_must_match_threshold_snapshot(db: Session) -> None:
    analyst = make_user(db)
    risk = make_risk(db, analyst)
    with expect_db_error(db, "appetite_flag_matches"):
        db.add(assessment(risk, analyst, 2, 5, above_appetite=False))  # 10 >= 10 is above


def test_valid_assessment_l4_i5_is_stored(db: Session) -> None:
    analyst = make_user(db)
    risk = make_risk(db, analyst)
    db.add(assessment(risk, analyst, 4, 5))
    db.flush()
    stored = db.exec(text("SELECT score, band, above_appetite FROM risk_assessment")).one()  # type: ignore[call-overload]
    assert (stored[0], stored[1], bool(stored[2])) == (20, "critical", True)


def test_only_one_initial_assessment_per_risk(db: Session) -> None:
    analyst = make_user(db)
    risk = make_risk(db, analyst)
    db.add(assessment(risk, analyst, 3, 3))
    db.flush()
    with expect_db_error(db, ("uq_risk_assessment_one_initial", "risk_assessment.risk_id")):
        db.add(assessment(risk, analyst, 2, 2))
    db.add(assessment(risk, analyst, 2, 2, assessment_type="reassessment"))
    db.flush()  # reassessments are unlimited


def test_rationale_is_required(db: Session) -> None:
    analyst = make_user(db)
    risk = make_risk(db, analyst)
    with expect_db_error(db, "rationale_required"):
        db.add(assessment(risk, analyst, 2, 2, rationale="   "))


# ── Insert-only tables (T11 at database level) ─────────────────────────────────────────────


def _seed_insert_only_rows(db: Session) -> None:
    analyst = make_user(db)
    risk = make_risk(db, analyst)
    db.add(assessment(risk, analyst, 3, 4))
    db.add(
        TreatmentDecision(
            risk_id=risk.id, strategy="reduce", justification="Fix it", decided_by_id=analyst.id
        )
    )
    db.add(
        Evidence(
            target_type="risk",
            target_id=risk.id,
            original_name="e.pdf",
            mime_type="application/pdf",
            size_bytes=3,
            sha256="a" * 64,
            content=b"pdf",
            uploaded_by_id=analyst.id,
        )
    )
    db.add(AuditLog(action="CREATE", prev_hash=GENESIS_HASH, hash="b" * 64))
    db.flush()


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE risk_assessment SET rationale = 'rewritten'",
        "DELETE FROM risk_assessment",
        "UPDATE treatment_decision SET justification = 'rewritten'",
        "DELETE FROM treatment_decision",
        "UPDATE evidence SET original_name = 'other.pdf'",
        "DELETE FROM evidence",
        "UPDATE audit_log SET action = 'UPDATE'",
        "DELETE FROM audit_log",
    ],
)
def test_insert_only_tables_refuse_update_and_delete(db: Session, statement: str) -> None:
    _seed_insert_only_rows(db)
    with expect_db_error(db, "insert-only"):
        db.exec(text(statement))  # type: ignore[call-overload]


def test_audit_chain_cannot_fork(db: Session) -> None:
    db.add(AuditLog(action="CREATE", prev_hash=GENESIS_HASH, hash="c" * 64))
    db.flush()
    with expect_db_error(db):
        db.add(AuditLog(action="CREATE", prev_hash=GENESIS_HASH, hash="d" * 64))


# ── Register ───────────────────────────────────────────────────────────────────────────────


def test_asset_name_unique_within_a_service_only(db: Session) -> None:
    s1, s2 = make_service(db), make_service(db)
    make_asset(db, s1, name="Customer database")
    make_asset(db, s2, name="Customer database")  # same name, other service: allowed
    with expect_db_error(db, ("uq_asset_name_service", "asset.name, asset.service_id")):
        make_asset(db, s1, name="Customer database")


def test_codes_must_follow_their_format(db: Session) -> None:
    analyst = make_user(db)
    with expect_db_error(db, "risk_code_format"):
        make_risk(db, analyst, risk_code="X-001")


def test_unknown_role_rejected(db: Session) -> None:
    with expect_db_error(db, "role_allowed"):
        make_user(db, role=Role.ANALYST, username="badrole").role = "superuser"
        db.flush()


# ── Treatment and acceptance ───────────────────────────────────────────────────────────────


def test_completed_action_must_record_who_when_and_note(db: Session) -> None:
    owner = make_user(db, Role.OWNER)
    risk = make_risk(db, owner)
    with expect_db_error(db, "completion_recorded"):
        db.add(
            TreatmentAction(
                action_code="T-900",
                risk_id=risk.id,
                title="Patch",
                owner_id=owner.id,
                due_date=future(),
                status="completed",
                created_by_id=owner.id,
            )
        )


def test_acceptance_justification_needs_30_characters(db: Session) -> None:
    owner = make_user(db, Role.OWNER)
    risk = make_risk(db, owner)
    with expect_db_error(db, "justification_length"):
        db.add(
            AcceptanceRequest(
                risk_id=risk.id,
                requested_by_id=owner.id,
                justification="Too short to justify.",
                proposed_expiry=future(),
            )
        )


def test_requester_can_never_decide_own_acceptance(db: Session) -> None:
    owner = make_user(db, Role.OWNER)
    risk = make_risk(db, owner)
    with expect_db_error(db, "requester_cannot_decide"):
        db.add(
            AcceptanceRequest(
                risk_id=risk.id,
                requested_by_id=owner.id,
                justification="Compensating controls are in place for this risk.",
                proposed_expiry=future(),
                status="approved",
                decided_by_id=owner.id,
                decision_date=datetime.now(UTC),
                expiry_date=future(),
            )
        )


def test_approved_acceptance_needs_decider_date_and_expiry(db: Session) -> None:
    owner, cro = make_user(db, Role.OWNER), make_user(db, Role.APPROVER)
    risk = make_risk(db, owner)
    base = {
        "risk_id": risk.id,
        "requested_by_id": owner.id,
        "proposed_expiry": future(),
        "justification": "Compensating controls are in place for this risk.",
    }
    # Breaks two rules at once; databases differ in which one they report first.
    with expect_db_error(db, ("decision_recorded", "approval_has_expiry")):
        db.add(AcceptanceRequest(**base, status="approved", decided_by_id=cro.id))
    with expect_db_error(db, "approval_has_expiry"):
        db.add(
            AcceptanceRequest(
                **base, status="approved", decided_by_id=cro.id, decision_date=datetime.now(UTC)
            )
        )
    db.add(
        AcceptanceRequest(
            **base,
            status="approved",
            decided_by_id=cro.id,
            decision_date=datetime.now(UTC),
            expiry_date=future(),
        )
    )
    db.flush()


# ── Evidence and settings ──────────────────────────────────────────────────────────────────


def test_evidence_over_4_mb_rejected(db: Session) -> None:
    analyst = make_user(db)
    with expect_db_error(db, "size_limit"):
        db.add(
            Evidence(
                target_type="risk",
                target_id=1,
                original_name="big.pdf",
                mime_type="application/pdf",
                size_bytes=EVIDENCE_MAX_BYTES + 1,
                sha256="a" * 64,
                content=b"x",
                uploaded_by_id=analyst.id,
            )
        )


def test_settings_table_holds_a_single_row(db: Session) -> None:
    with expect_db_error(db, "single_row"):
        db.add(AppSetting(id=2))
    assert db.exec(select(AppSetting)).one().appetite_threshold == 10


# ── Time handling ──────────────────────────────────────────────────────────────────────────


def test_timestamps_round_trip_as_aware_utc(db: Session) -> None:
    eat = timezone(timedelta(hours=3))
    written = datetime(2026, 12, 5, 23, 30, tzinfo=eat)  # 23:30 in Kampala
    user = make_user(db, last_login_at=written)
    db.expire(user)
    read = db.get(type(user), user.id).last_login_at  # type: ignore[union-attr]
    assert read is not None and read.tzinfo is not None
    assert read == written
    assert read.utcoffset() == timedelta(0)
    assert (read.hour, read.minute) == (20, 30)  # stored and returned in UTC


def test_naive_datetimes_are_refused(db: Session) -> None:
    with pytest.raises(Exception, match="naive datetime"):
        make_user(db, last_login_at=datetime(2026, 12, 5, 12, 0))  # noqa: DTZ001
