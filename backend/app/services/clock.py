"""The only place the application reads the current time (PLAN.md §2.7).

- `now_utc()` for timestamps: always timezone-aware UTC.
- `org_today()` for business dates: the calendar date in The Alajo's official zone, so an
  action due on 5 Dec becomes overdue at 00:00 WAT on 6 Dec for every user.

Tests replace `_now` to freeze time.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo


def _system_now() -> datetime:
    return datetime.now(UTC)


_now: Callable[[], datetime] = _system_now


def now_utc() -> datetime:
    return _now().astimezone(UTC)


def org_today(org_timezone: str = "Africa/Lagos") -> date:
    return now_utc().astimezone(ZoneInfo(org_timezone)).date()
