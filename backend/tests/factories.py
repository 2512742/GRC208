"""Small builders for valid rows, so each test states only what it is about."""

from __future__ import annotations

import itertools
from contextlib import contextmanager
from datetime import date, timedelta
from typing import Any

import pytest
from sqlalchemy.exc import DBAPIError
from sqlmodel import Session

from app.models import Asset, BusinessService, Risk, RiskAssessment, User
from app.models.enums import Role

_seq = itertools.count(1)


def _n() -> int:
    return next(_seq)


def make_user(db: Session, role: Role = Role.ANALYST, **kw: Any) -> User:
    n = _n()
    user = User(
        username=kw.pop("username", f"user{n}"),
        full_name=kw.pop("full_name", f"Test User {n}"),
        password_hash="not-a-real-hash",
        role=role.value,
        **kw,
    )
    db.add(user)
    db.flush()
    return user


def make_service(db: Session, **kw: Any) -> BusinessService:
    n = _n()
    service = BusinessService(
        code=kw.pop("code", f"S{n}"), name=kw.pop("name", f"Service {n}"), **kw
    )
    db.add(service)
    db.flush()
    return service


def make_asset(db: Session, service: BusinessService, **kw: Any) -> Asset:
    n = _n()
    asset = Asset(
        asset_code=kw.pop("asset_code", f"A-{n:03d}"),
        name=kw.pop("name", f"Asset {n}"),
        asset_type=kw.pop("asset_type", "application"),
        service_id=service.id,
        **kw,
    )
    db.add(asset)
    db.flush()
    return asset


def make_risk(db: Session, owner: User, creator: User | None = None, **kw: Any) -> Risk:
    n = _n()
    risk = Risk(
        risk_code=kw.pop("risk_code", f"R-{n:03d}"),
        title=kw.pop("title", f"Test risk number {n}"),
        description="desc",
        threat="threat",
        vulnerability="vuln",
        business_impact="impact",
        owner_id=owner.id,
        created_by_id=(creator or owner).id,
        **kw,
    )
    db.add(risk)
    db.flush()
    return risk


def assessment(
    risk: Risk, assessor: User, likelihood: int, impact: int, **kw: Any
) -> RiskAssessment:
    """A *consistent* assessment row (score, band and flag computed as the methodology says)."""
    score = likelihood * impact
    band = (
        "low" if score <= 4 else "medium" if score <= 9 else "high" if score <= 14 else "critical"
    )
    threshold = kw.pop("appetite_threshold", 10)
    values: dict[str, Any] = {
        "risk_id": risk.id,
        "assessment_type": "initial",
        "likelihood": likelihood,
        "impact": impact,
        "score": score,
        "band": band,
        "above_appetite": score >= threshold,
        "appetite_threshold": threshold,
        "rationale": "Because the evidence says so.",
        "assessed_by_id": assessor.id,
    }
    values.update(kw)
    return RiskAssessment(**values)


def future(days: int = 90) -> date:
    return date.today() + timedelta(days=days)  # test data only; app code uses services.clock


@contextmanager
def expect_db_error(db: Session, match: str | tuple[str, ...] | None = None):  # type: ignore[no-untyped-def]
    """Assert the block raises a database error, inside a savepoint so the test can go on
    (PostgreSQL aborts the whole transaction otherwise)."""
    savepoint = db.begin_nested()
    with pytest.raises(DBAPIError) as info:
        yield
        db.flush()
    savepoint.rollback()
    if match:
        # PostgreSQL names the constraint; SQLite names the columns. Accept either wording.
        options = (match,) if isinstance(match, str) else match
        message = str(info.value).lower()
        assert any(option.lower() in message for option in options), str(info.value)
