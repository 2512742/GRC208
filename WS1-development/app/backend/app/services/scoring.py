"""Risk scoring methodology (PLAN.md §2.4), as pure functions.

score = likelihood x impact (each 1 to 5)
bands:  1-4 Low, 5-9 Medium, 10-14 High, 15-25 Critical
appetite: score >= threshold (default 10) is above appetite

The database repeats these rules as CHECK constraints; this module is what the API calls, and
the explanation text is what users see ("show users how each score was calculated").
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from app.models.enums import Band

LIKELIHOOD_LABELS: dict[int, str] = {
    1: "Rare",
    2: "Unlikely",
    3: "Possible",
    4: "Likely",
    5: "Almost certain",
}
IMPACT_LABELS: dict[int, str] = {
    1: "Negligible",
    2: "Minor",
    3: "Moderate",
    4: "Major",
    5: "Severe",
}
# What each level means. Drafts taken from the group's prototype, with its US-dollar loss
# figures left out: the risk framework team adds the ₦ ranges through the settings, which
# override these defaults (AppSetting.likelihood_definitions / impact_definitions).
DEFAULT_LIKELIHOOD_DEFINITIONS: tuple[str, ...] = (
    "May occur only in exceptional circumstances (under 5% chance in 12 months).",
    "Could occur at some time (5% to 20%); needs a targeted attacker and several control failures.",
    "Might occur (21% to 50%); known exploit patterns exist and exposure is moderate.",
    "Will probably occur (51% to 80%); active scanning or attack campaigns have been seen.",
    "Expected to occur (over 80%); an exposed weakness or a recurring incident.",
)
DEFAULT_IMPACT_DEFINITIONS: tuple[str, ...] = (
    "Minimal disruption (under 1 hour); negligible financial loss; no regulatory or customer "
    "impact.",
    "Local service degradation (1 to 4 hours); minor financial loss; fixed internally.",
    "Significant disruption to a business unit (4 to 24 hours); moderate financial loss; "
    "reportable incident.",
    "Critical outage (24 to 72 hours); major financial loss; regulatory inquiry and customer "
    "churn.",
    "Systemic failure (over 72 hours); severe financial loss; major data breach, sanctions or "
    "licence risk.",
)
LEVEL_COUNT = 5

BAND_LABELS: dict[Band, str] = {
    Band.LOW: "Low",
    Band.MEDIUM: "Medium",
    Band.HIGH: "High",
    Band.CRITICAL: "Critical",
}


class ScoringError(ValueError):
    """Likelihood or impact outside 1-5, or an invalid threshold."""


@dataclass(frozen=True)
class GovernancePolicy:
    """Tunable numbers from the `app_setting` row. Defaults match the methodology."""

    appetite_threshold: int = 10
    sla_days_critical: int = 30
    sla_days_high: int = 90
    sla_days_medium: int = 180
    review_days_critical: int = 30
    review_days_high: int = 90
    review_days_medium: int = 180
    review_days_low: int = 365
    review_warning_days: int = 30

    @classmethod
    def from_setting(cls, setting: object) -> GovernancePolicy:
        """Build from an AppSetting row (or anything with the same attribute names)."""
        names = cls.__dataclass_fields__.keys()
        return cls(**{name: getattr(setting, name) for name in names})

    def sla_days(self, band: Band) -> int | None:
        """Days allowed to remediate; Low has no SLA."""
        return {
            Band.CRITICAL: self.sla_days_critical,
            Band.HIGH: self.sla_days_high,
            Band.MEDIUM: self.sla_days_medium,
            Band.LOW: None,
        }[band]

    def review_days(self, band: Band) -> int:
        return {
            Band.CRITICAL: self.review_days_critical,
            Band.HIGH: self.review_days_high,
            Band.MEDIUM: self.review_days_medium,
            Band.LOW: self.review_days_low,
        }[band]


DEFAULT_POLICY = GovernancePolicy()


@dataclass(frozen=True)
class ScoreResult:
    likelihood: int
    impact: int
    score: int
    band: Band
    above_appetite: bool
    appetite_threshold: int
    sla_days: int | None

    @property
    def band_label(self) -> str:
        return BAND_LABELS[self.band]

    @property
    def explanation(self) -> str:
        """e.g. 'Likelihood 4 (Likely) × Impact 5 (Severe) = 20 → Critical. Above appetite
        (threshold 10). Remediation due within 30 days.'"""
        text = (
            f"Likelihood {self.likelihood} ({LIKELIHOOD_LABELS[self.likelihood]}) × "
            f"Impact {self.impact} ({IMPACT_LABELS[self.impact]}) = {self.score} → "
            f"{self.band_label}. "
        )
        if self.above_appetite:
            text += f"Above appetite (threshold {self.appetite_threshold})."
        else:
            text += f"Within appetite (threshold {self.appetite_threshold})."
        if self.sla_days is not None:
            text += f" Remediation due within {self.sla_days} days."
        return text


def band_for(score: int) -> Band:
    if not 1 <= score <= 25:
        raise ScoringError(f"score must be 1-25, got {score}")
    if score <= 4:
        return Band.LOW
    if score <= 9:
        return Band.MEDIUM
    if score <= 14:
        return Band.HIGH
    return Band.CRITICAL


def _check_scale(name: str, value: int) -> None:
    # bool is an int subclass; True/False are never valid scores.
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
        raise ScoringError(f"{name} must be a whole number from 1 to 5, got {value!r}")


def score_risk(
    likelihood: int, impact: int, policy: GovernancePolicy = DEFAULT_POLICY
) -> ScoreResult:
    _check_scale("likelihood", likelihood)
    _check_scale("impact", impact)
    if not 1 <= policy.appetite_threshold <= 25:
        raise ScoringError(f"appetite threshold must be 1-25, got {policy.appetite_threshold}")
    score = likelihood * impact
    band = band_for(score)
    return ScoreResult(
        likelihood=likelihood,
        impact=impact,
        score=score,
        band=band,
        above_appetite=score >= policy.appetite_threshold,
        appetite_threshold=policy.appetite_threshold,
        sla_days=policy.sla_days(band),
    )


def remediation_due(
    band: Band, today: date, policy: GovernancePolicy = DEFAULT_POLICY
) -> date | None:
    """Default due date for a new treatment action: today (org zone) + the band's SLA."""
    days = policy.sla_days(band)
    return today + timedelta(days=days) if days is not None else None


def next_review(band: Band, assessed_on: date, policy: GovernancePolicy = DEFAULT_POLICY) -> date:
    return assessed_on + timedelta(days=policy.review_days(band))


def review_is_upcoming(
    review_date: date | None, today: date, policy: GovernancePolicy = DEFAULT_POLICY
) -> bool:
    """Due within the warning window (including overdue reviews)."""
    if review_date is None:
        return False
    return review_date <= today + timedelta(days=policy.review_warning_days)
