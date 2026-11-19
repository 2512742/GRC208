"""Status lifecycles (PLAN.md §2.3) and the statuses computed at read time.

Every status change in the API goes through `check_transition`; anything not listed is refused.
"Overdue" and "acceptance expired" are never stored: they are computed from dates in the
organisation's zone, so they are always current without a scheduler (serverless-friendly).
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from app.models.enums import AcceptanceStatus, ActionStatus, RiskStatus


class InvalidTransition(ValueError):
    def __init__(self, kind: str, current: str, target: str) -> None:
        super().__init__(f"{kind} cannot move from '{current}' to '{target}'")
        self.kind, self.current, self.target = kind, current, target


R = RiskStatus
RISK_TRANSITIONS: dict[RiskStatus, frozenset[RiskStatus]] = {
    # Treatment starts, acceptance is approved, or (after a reassessment) the risk is closed.
    R.OPEN: frozenset({R.TREATMENT_IN_PROGRESS, R.ACCEPTED, R.CLOSED}),
    # An action completes, an acceptance is approved, or the last action is cancelled.
    R.TREATMENT_IN_PROGRESS: frozenset({R.AWAITING_REASSESSMENT, R.ACCEPTED, R.OPEN}),
    # Only a reassessment moves it on.
    R.AWAITING_REASSESSMENT: frozenset({R.OPEN, R.TREATMENT_IN_PROGRESS, R.ACCEPTED, R.CLOSED}),
    # An acceptance expired or was withdrawn: back to review or treatment.
    R.ACCEPTED: frozenset({R.OPEN, R.TREATMENT_IN_PROGRESS}),
    R.CLOSED: frozenset({R.OPEN}),
}

A = ActionStatus
ACTION_TRANSITIONS: dict[ActionStatus, frozenset[ActionStatus]] = {
    A.NOT_STARTED: frozenset({A.IN_PROGRESS, A.COMPLETED, A.CANCELLED}),
    A.IN_PROGRESS: frozenset({A.COMPLETED, A.CANCELLED}),
    A.COMPLETED: frozenset(),  # final: completion is evidence-backed history
    A.CANCELLED: frozenset(),
}

C = AcceptanceStatus
ACCEPTANCE_TRANSITIONS: dict[AcceptanceStatus, frozenset[AcceptanceStatus]] = {
    C.PENDING: frozenset({C.APPROVED, C.REJECTED}),
    C.APPROVED: frozenset(),  # a new request is needed after expiry
    C.REJECTED: frozenset(),
}

_TABLES: dict[str, dict] = {  # type: ignore[type-arg]
    "risk": RISK_TRANSITIONS,
    "action": ACTION_TRANSITIONS,
    "acceptance": ACCEPTANCE_TRANSITIONS,
}
_ENUMS: dict[str, type[StrEnum]] = {
    "risk": RiskStatus,
    "action": ActionStatus,
    "acceptance": AcceptanceStatus,
}


def can_transition(kind: str, current: str, target: str) -> bool:
    enum = _ENUMS[kind]
    try:
        return enum(target) in _TABLES[kind][enum(current)]
    except ValueError:
        return False  # unknown status value


def check_transition(kind: str, current: str, target: str) -> None:
    if not can_transition(kind, current, target):
        raise InvalidTransition(kind, current, target)


# ── Computed at read time ──────────────────────────────────────────────────────────────────

OPEN_ACTION_STATUSES = frozenset({ActionStatus.NOT_STARTED.value, ActionStatus.IN_PROGRESS.value})


def action_is_overdue(status: str, due_date: date, today: date) -> bool:
    """Overdue the day *after* the due date, in the organisation's zone (test T32)."""
    return status in OPEN_ACTION_STATUSES and due_date < today


def acceptance_is_expired(status: str, expiry_date: date | None, today: date) -> bool:
    """Valid through its expiry date; expired from the next day."""
    return (
        status == AcceptanceStatus.APPROVED.value
        and expiry_date is not None
        and expiry_date < today
    )


def display_risk_status(status: str, acceptance_expired: bool) -> str:
    """What screens and reports show: an accepted risk whose acceptance lapsed needs review."""
    if status == RiskStatus.ACCEPTED.value and acceptance_expired:
        return "acceptance_expired"
    return status
