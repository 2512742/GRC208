"""P2 scoring: T01 (L4 x I5 = 20), T03 (every combination), T04 (the 9/10 boundary)."""

from __future__ import annotations

from datetime import date

import pytest
from sqlmodel import Session

from app.models import RiskAssessment
from app.models.enums import Band
from app.services.scoring import (
    DEFAULT_POLICY,
    GovernancePolicy,
    ScoringError,
    band_for,
    next_review,
    remediation_due,
    review_is_upcoming,
    score_risk,
)
from tests.factories import make_risk, make_user

# Written out by hand from the methodology, independent of the code under test.
# Rows: likelihood 1..5; columns: impact 1..5.
EXPECTED_BAND = {
    1: ["low", "low", "low", "low", "medium"],
    2: ["low", "low", "medium", "medium", "high"],
    3: ["low", "medium", "medium", "high", "critical"],
    4: ["low", "medium", "high", "critical", "critical"],
    5: ["medium", "high", "critical", "critical", "critical"],
}
ALL_PAIRS = [(lk, im) for lk in range(1, 6) for im in range(1, 6)]


@pytest.mark.parametrize(("likelihood", "impact"), ALL_PAIRS)
def test_every_combination_matches_the_methodology(likelihood: int, impact: int) -> None:
    result = score_risk(likelihood, impact)
    assert result.score == likelihood * impact
    assert result.band.value == EXPECTED_BAND[likelihood][impact - 1]
    assert result.above_appetite is (likelihood * impact >= 10)


def test_t01_l4_i5_is_20_critical_above_appetite_with_explanation() -> None:
    result = score_risk(4, 5)
    assert (result.score, result.band, result.above_appetite) == (20, Band.CRITICAL, True)
    assert result.explanation == (
        "Likelihood 4 (Likely) × Impact 5 (Severe) = 20 → Critical. "
        "Above appetite (threshold 10). Remediation due within 30 days."
    )


def test_t04_boundary_nine_within_ten_above() -> None:
    nine, ten = score_risk(3, 3), score_risk(2, 5)
    assert (nine.score, nine.above_appetite, nine.band) == (9, False, Band.MEDIUM)
    assert (ten.score, ten.above_appetite, ten.band) == (10, True, Band.HIGH)
    assert "Within appetite (threshold 10)" in nine.explanation
    assert "Above appetite (threshold 10)" in ten.explanation


def test_low_band_has_no_remediation_deadline_in_explanation() -> None:
    assert score_risk(1, 2).explanation == (
        "Likelihood 1 (Rare) × Impact 2 (Minor) = 2 → Low. Within appetite (threshold 10)."
    )


def test_threshold_comes_from_policy() -> None:
    strict = GovernancePolicy(appetite_threshold=6)
    assert score_risk(2, 3, strict).above_appetite is True
    assert score_risk(1, 5, strict).above_appetite is False


@pytest.mark.parametrize("bad", [0, 6, -1, 2.5, "3", True, None])
def test_t02_values_outside_1_to_5_rejected(bad: object) -> None:
    with pytest.raises(ScoringError):
        score_risk(bad, 3)  # type: ignore[arg-type]
    with pytest.raises(ScoringError):
        score_risk(3, bad)  # type: ignore[arg-type]


def test_invalid_threshold_rejected() -> None:
    with pytest.raises(ScoringError):
        score_risk(3, 3, GovernancePolicy(appetite_threshold=0))


@pytest.mark.parametrize(
    ("score", "band"),
    [
        (1, "low"),
        (4, "low"),
        (5, "medium"),
        (9, "medium"),
        (10, "high"),
        (14, "high"),
        (15, "critical"),
        (25, "critical"),
    ],
)
def test_band_edges(score: int, band: str) -> None:
    assert band_for(score).value == band


@pytest.mark.parametrize("score", [0, 26])
def test_band_for_rejects_impossible_scores(score: int) -> None:
    with pytest.raises(ScoringError):
        band_for(score)


def test_remediation_due_dates_follow_band_sla() -> None:
    today = date(2026, 12, 1)
    assert remediation_due(Band.CRITICAL, today) == date(2026, 12, 31)
    assert remediation_due(Band.HIGH, today) == date(2027, 3, 1)
    assert remediation_due(Band.MEDIUM, today) == date(2027, 5, 30)
    assert remediation_due(Band.LOW, today) is None


def test_review_cycle_and_upcoming_window() -> None:
    assessed = date(2026, 12, 1)
    assert next_review(Band.CRITICAL, assessed) == date(2026, 12, 31)
    assert next_review(Band.LOW, assessed) == date(2027, 12, 1)
    today = date(2026, 12, 1)
    assert review_is_upcoming(date(2026, 12, 31), today) is True  # exactly 30 days away
    assert review_is_upcoming(date(2027, 1, 1), today) is False
    assert review_is_upcoming(date(2026, 11, 1), today) is True  # overdue review counts
    assert review_is_upcoming(None, today) is False


def test_policy_reads_an_app_setting_row(db: Session) -> None:
    from sqlmodel import select

    from app.models import AppSetting

    policy = GovernancePolicy.from_setting(db.exec(select(AppSetting)).one())
    assert policy == DEFAULT_POLICY


@pytest.mark.parametrize(("likelihood", "impact"), ALL_PAIRS)
def test_code_and_database_agree_for_every_combination(
    db: Session, likelihood: int, impact: int
) -> None:
    """Every result the scoring code produces satisfies the database's own CHECK rules."""
    analyst = make_user(db)
    risk = make_risk(db, analyst)
    result = score_risk(likelihood, impact)
    db.add(
        RiskAssessment(
            risk_id=risk.id,
            assessment_type="initial",
            likelihood=likelihood,
            impact=impact,
            score=result.score,
            band=result.band.value,
            above_appetite=result.above_appetite,
            appetite_threshold=result.appetite_threshold,
            rationale="checked",
            assessed_by_id=analyst.id,
        )
    )
    db.flush()
