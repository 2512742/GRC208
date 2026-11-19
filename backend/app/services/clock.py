"""The only place the application reads the current time (PLAN.md §2.7).

- `now_utc()` for timestamps: always timezone-aware UTC.
- `org_today()` for business dates: the calendar date in The Alajo's official zone, so an
  action due on 5 Dec becomes overdue at 00:00 WAT on 6 Dec for every user, wherever they are.

Tests use `frozen(...)` to fix the time.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

DEFAULT_ORG_TIMEZONE = "Africa/Lagos"


def _system_now() -> datetime:
    return datetime.now(UTC)


_now: Callable[[], datetime] = _system_now


def now_utc() -> datetime:
    return _now().astimezone(UTC)


def org_today(org_timezone: str = DEFAULT_ORG_TIMEZONE) -> date:
    return now_utc().astimezone(ZoneInfo(org_timezone)).date()


@contextmanager
def frozen(at: datetime) -> Iterator[None]:
    """Fix the clock at `at` (must be timezone-aware) for the duration of the block."""
    if at.tzinfo is None:
        raise ValueError("frozen() needs a timezone-aware datetime")
    global _now
    previous = _now
    _now = lambda: at  # noqa: E731
    try:
        yield
    finally:
        _now = previous
