"""Reading the governance settings row (appetite, SLAs, review cycles, official zone)."""

from __future__ import annotations

from datetime import date

from sqlmodel import Session

from app.models import AppSetting
from app.services import clock
from app.services.scoring import GovernancePolicy


def app_setting(session: Session) -> AppSetting:
    setting = session.get(AppSetting, 1)
    if setting is None:  # the baseline migration always creates it
        raise RuntimeError("app_setting row missing: run `alembic upgrade head`")
    return setting


def policy(session: Session) -> GovernancePolicy:
    return GovernancePolicy.from_setting(app_setting(session))


def org_today(session: Session) -> date:
    return clock.org_today(app_setting(session).org_timezone)
