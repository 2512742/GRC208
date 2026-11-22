"""P2: status lifecycles, read-time statuses and the WAT business clock (T16, T32)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from app.models.enums import AcceptanceStatus, ActionStatus, RiskStatus
from app.services import clock
from app.services.workflow import (
    ACCEPTANCE_TRANSITIONS,
    ACTION_TRANSITIONS,
    RISK_TRANSITIONS,
    InvalidTransition,
    acceptance_is_expired,
    action_is_overdue,
    can_transition,
    check_transition,
    display_risk_status,
)

TABLES = [
    ("risk", RiskStatus, RISK_TRANSITIONS),
    ("action", ActionStatus, ACTION_TRANSITIONS),
    ("acceptance", AcceptanceStatus, ACCEPTANCE_TRANSITIONS),
]


def _all_pairs():  # type: ignore[no-untyped-def]
    for kind, enum, table in TABLES:
        for current in enum:
            for target in enum:
                yield kind, current.value, target.value, target in table[current]


@pytest.mark.parametrize(("kind", "current", "target", "allowed"), list(_all_pairs()))
def test_every_transition_is_explicitly_allowed_or_refused(
    kind: str, current: str, target: str, allowed: bool
) -> None:
    assert can_transition(kind, current, target) is allowed
    if allowed:
        check_transition(kind, current, target)
    else:
        with pytest.raises(InvalidTransition):
            check_transition(kind, current, target)


def test_every_status_has_an_entry() -> None:
    for _, enum, table in TABLES:
        assert set(table) == set(enum)


def test_no_status_moves_to_itself() -> None:
    for _, _, table in TABLES:
        for current, targets in table.items():
            assert current not in targets


def test_completed_actions_and_decided_acceptances_are_final() -> None:
    assert ACTION_TRANSITIONS[ActionStatus.COMPLETED] == frozenset()
    assert ACCEPTANCE_TRANSITIONS[AcceptanceStatus.APPROVED] == frozenset()
    assert ACCEPTANCE_TRANSITIONS[AcceptanceStatus.REJECTED] == frozenset()


def test_completing_an_action_never_closes_the_risk_directly() -> None:
    """Brief feature 4: completion leads to 'awaiting reassessment', not to a lower score."""
    assert not can_transition("risk", "treatment_in_progress", "closed")


def test_unknown_status_values_are_refused() -> None:
    assert can_transition("risk", "open", "deleted") is False
    assert can_transition("action", "paused", "completed") is False


# ── Read-time statuses ─────────────────────────────────────────────────────────────────────


def test_overdue_starts_the_day_after_the_due_date() -> None:
    due = date(2026, 12, 5)
    assert action_is_overdue("in_progress", due, date(2026, 12, 5)) is False
    assert action_is_overdue("in_progress", due, date(2026, 12, 6)) is True
    assert action_is_overdue("not_started", due, date(2026, 12, 6)) is True
    assert action_is_overdue("completed", due, date(2027, 1, 1)) is False
    assert action_is_overdue("cancelled", due, date(2027, 1, 1)) is False


def test_t16_acceptance_valid_through_expiry_then_expired() -> None:
    expiry = date(2026, 12, 31)
    assert acceptance_is_expired("approved", expiry, date(2026, 12, 31)) is False
    assert acceptance_is_expired("approved", expiry, date(2027, 1, 1)) is True
    assert acceptance_is_expired("pending", expiry, date(2027, 1, 1)) is False
    assert acceptance_is_expired("rejected", expiry, date(2027, 1, 1)) is False
    assert display_risk_status("accepted", True) == "acceptance_expired"
    assert display_risk_status("accepted", False) == "accepted"
    assert display_risk_status("open", True) == "open"


# ── Clock (T32) ────────────────────────────────────────────────────────────────────────────

EAT = timezone(timedelta(hours=3))


def test_t32_due_today_not_overdue_at_2330_eat_but_overdue_after_wat_midnight() -> None:
    due = date(2026, 12, 5)
    # 23:30 in Kampala = 21:30 in Lagos: still 5 Dec for The Alajo.
    with clock.frozen(datetime(2026, 12, 5, 23, 30, tzinfo=EAT)):
        today = clock.org_today()
        assert today == date(2026, 12, 5)
        assert action_is_overdue("in_progress", due, today) is False
    # 02:30 in Kampala on 6 Dec = 00:30 in Lagos: overdue for everyone.
    with clock.frozen(datetime(2026, 12, 6, 2, 30, tzinfo=EAT)):
        today = clock.org_today()
        assert today == date(2026, 12, 6)
        assert action_is_overdue("in_progress", due, today) is True


def test_org_today_depends_on_the_org_zone_not_utc() -> None:
    # 23:30 UTC on 5 Dec is already 6 Dec in Lagos (UTC+1).
    with clock.frozen(datetime(2026, 12, 5, 23, 30, tzinfo=UTC)):
        assert clock.org_today("Africa/Lagos") == date(2026, 12, 6)
        assert clock.org_today("UTC") == date(2026, 12, 5)


def test_frozen_restores_the_real_clock_and_refuses_naive_times() -> None:
    with clock.frozen(datetime(2000, 1, 1, tzinfo=UTC)):
        assert clock.now_utc().year == 2000
    assert clock.now_utc().year >= 2026
    with pytest.raises(ValueError, match="timezone-aware"), clock.frozen(datetime(2000, 1, 1)):  # noqa: DTZ001
        pass
