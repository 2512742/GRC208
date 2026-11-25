"""Reading the governance settings row (appetite, SLAs, review cycles, official zone)."""

from __future__ import annotations

from datetime import date

from sqlmodel import Session

from app.models import AppSetting
from app.services import clock
from app.services.scoring import (
    DEFAULT_IMPACT_DEFINITIONS,
    DEFAULT_LIKELIHOOD_DEFINITIONS,
    LEVEL_COUNT,
    GovernancePolicy,
)


def app_setting(session: Session) -> AppSetting:
    setting = session.get(AppSetting, 1)
    if setting is None:  # the baseline migration always creates it
        raise RuntimeError("app_setting row missing: run `alembic upgrade head`")
    return setting


def policy(session: Session) -> GovernancePolicy:
    return GovernancePolicy.from_setting(app_setting(session))


def org_today(session: Session) -> date:
    return clock.org_today(app_setting(session).org_timezone)


def level_definitions(setting: AppSetting) -> tuple[list[str], list[str]]:
    """(likelihood, impact) definitions for levels 1 to 5: the settings, or the defaults."""

    def pick(stored: list[str] | None, default: tuple[str, ...]) -> list[str]:
        if stored and len(stored) == LEVEL_COUNT and all(isinstance(t, str) for t in stored):
            return list(stored)
        return list(default)

    return (
        pick(setting.likelihood_definitions, DEFAULT_LIKELIHOOD_DEFINITIONS),
        pick(setting.impact_definitions, DEFAULT_IMPACT_DEFINITIONS),
    )
