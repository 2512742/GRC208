"""Register operations shared by the API, `seed-demo` and the CSV import.

Each function validates, writes, and appends the audit entry in the caller's transaction; the
caller commits. Nothing here knows about HTTP.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from datetime import date
from typing import Any

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.models import (
    Asset,
    AssetObligation,
    BusinessService,
    Obligation,
    Risk,
    RiskAssessment,
    RiskAsset,
    RiskObligation,
    User,
)
from app.models.enums import AssessmentType, AuditAction, RiskStatus, Role
from app.services import audit, governance
from app.services.scoring import ScoreResult, next_review, score_risk

OWNER_ROLES = frozenset({Role.OWNER.value, Role.APPROVER.value})  # who may own a risk


class RegisterError(ValueError):
    """Invalid request; `status` hints the HTTP code (422 by default, 409 for conflicts)."""

    def __init__(self, message: str, status: int = 422) -> None:
        super().__init__(message)
        self.status = status


# ── Codes ──────────────────────────────────────────────────────────────────────────────────


def next_code(session: Session, column: Any, prefix: str, width: int = 3) -> str:
    """Next 'A-019' style code: highest existing number + 1 (gaps are never reused)."""
    codes = session.exec(select(column).where(column.like(f"{prefix}%"))).all()
    numbers = [
        int(m.group(1)) for c in codes if (m := re.fullmatch(rf"{re.escape(prefix)}(\d+)", c))
    ]
    return f"{prefix}{(max(numbers, default=0) + 1):0{width}d}"


# ── Snapshots for the audit log ────────────────────────────────────────────────────────────


def snapshot(row: Any, fields: Iterable[str]) -> dict[str, Any]:
    return {name: getattr(row, name) for name in fields}


SERVICE_FIELDS = ("code", "name", "description", "owner_id", "criticality")
ASSET_FIELDS = (
    "asset_code",
    "name",
    "asset_type",
    "service_id",
    "owner_id",
    "classification",
    "status",
    "description",
)
RISK_FIELDS = (
    "risk_code",
    "title",
    "description",
    "threat",
    "vulnerability",
    "business_impact",
    "category",
    "owner_id",
    "status",
    "next_review_date",
)


# ── Lookups and checks ─────────────────────────────────────────────────────────────────────


def require_ids(session: Session, model: Any, ids: Sequence[int], label: str) -> list[Any]:
    wanted = list(dict.fromkeys(ids))  # de-duplicate, keep order
    if not wanted:
        return []
    found = {row.id: row for row in session.exec(select(model).where(col(model.id).in_(wanted)))}
    missing = [i for i in wanted if i not in found]
    if missing:
        raise RegisterError(f"Unknown {label} id(s): {', '.join(map(str, missing))}.")
    return [found[i] for i in wanted]


def check_risk_owner(session: Session, owner_id: int) -> User:
    owner = session.get(User, owner_id)
    if owner is None or not owner.is_active:
        raise RegisterError("The risk owner must be an active user.")
    if owner.role not in OWNER_ROLES:
        raise RegisterError("A risk owner must have the owner or approver role.")
    return owner


def check_optional_user(session: Session, user_id: int | None, label: str) -> None:
    if user_id is not None:
        user = session.get(User, user_id)
        if user is None or not user.is_active:
            raise RegisterError(f"The {label} must be an active user.")


def asset_name_taken(
    session: Session, name: str, service_id: int, except_id: int | None = None
) -> bool:
    query = select(Asset.id).where(
        func.lower(Asset.name) == name.strip().lower(), Asset.service_id == service_id
    )
    if except_id is not None:
        query = query.where(Asset.id != except_id)
    return session.exec(query).first() is not None


# ── Services and assets ────────────────────────────────────────────────────────────────────


def create_service(session: Session, by: audit.AuditActor, **values: Any) -> BusinessService:
    if session.exec(
        select(BusinessService.id).where(
            (func.lower(BusinessService.code) == values["code"].lower())
            | (func.lower(BusinessService.name) == values["name"].lower())
        )
    ).first():
        raise RegisterError("A business service with that code or name already exists.", 409)
    check_optional_user(session, values.get("owner_id"), "service owner")
    service = BusinessService(**values)
    session.add(service)
    session.flush()
    audit.record(
        session,
        AuditAction.CREATE,
        by,
        object_type="service",
        object_id=service.id,
        after=snapshot(service, SERVICE_FIELDS),
    )
    return service


def create_asset(
    session: Session, by: audit.AuditActor, obligation_ids: Sequence[int] = (), **values: Any
) -> Asset:
    if session.get(BusinessService, values["service_id"]) is None:
        raise RegisterError(f"Unknown service id: {values['service_id']}.")
    if asset_name_taken(session, values["name"], values["service_id"]):
        raise RegisterError("An asset with this name already exists in that service.", 409)
    check_optional_user(session, values.get("owner_id"), "asset owner")
    obligations = require_ids(session, Obligation, obligation_ids, "obligation")
    if not values.get("asset_code"):
        values["asset_code"] = next_code(session, Asset.asset_code, "A-")
    elif session.exec(select(Asset.id).where(Asset.asset_code == values["asset_code"])).first():
        raise RegisterError(f"Asset code {values['asset_code']} is already used.", 409)
    values["name"] = values["name"].strip()
    asset = Asset(**values)
    session.add(asset)
    session.flush()
    for obligation in obligations:
        session.add(AssetObligation(asset_id=asset.id, obligation_id=obligation.id))
    audit.record(
        session,
        AuditAction.CREATE,
        by,
        object_type="asset",
        object_id=asset.id,
        after={**snapshot(asset, ASSET_FIELDS), "obligation_ids": [o.id for o in obligations]},
    )
    return asset


# ── Risks ──────────────────────────────────────────────────────────────────────────────────


def create_risk(
    session: Session,
    by: audit.AuditActor,
    *,
    asset_ids: Sequence[int],
    obligation_ids: Sequence[int] = (),
    risk_code: str | None = None,
    **values: Any,
) -> Risk:
    if not asset_ids:
        raise RegisterError("A risk must be linked to at least one asset.")
    assets = require_ids(session, Asset, asset_ids, "asset")
    obligations = require_ids(session, Obligation, obligation_ids, "obligation")
    check_risk_owner(session, values["owner_id"])
    if risk_code is None:
        risk_code = next_code(session, Risk.risk_code, "R-")
    elif session.exec(select(Risk.id).where(Risk.risk_code == risk_code)).first():
        raise RegisterError(f"Risk code {risk_code} is already used.", 409)

    risk = Risk(
        risk_code=risk_code,
        created_by_id=by.user_id or values["owner_id"],
        status=RiskStatus.OPEN.value,
        **values,
    )
    session.add(risk)
    session.flush()
    for asset in assets:
        session.add(RiskAsset(risk_id=risk.id, asset_id=asset.id))
    for obligation in obligations:
        session.add(RiskObligation(risk_id=risk.id, obligation_id=obligation.id))
    audit.record(
        session,
        AuditAction.CREATE,
        by,
        object_type="risk",
        object_id=risk.id,
        after={
            **snapshot(risk, RISK_FIELDS),
            "asset_ids": [a.id for a in assets],
            "obligation_ids": [o.id for o in obligations],
        },
    )
    return risk


def set_links(
    session: Session,
    risk: Risk,
    *,
    asset_ids: Sequence[int] | None = None,
    obligation_ids: Sequence[int] | None = None,
) -> dict[str, list[int]]:
    """Replace a risk's asset and/or obligation links; returns what changed for the audit."""
    changed: dict[str, list[int]] = {}
    if asset_ids is not None:
        if not asset_ids:
            raise RegisterError("A risk must be linked to at least one asset.")
        assets = require_ids(session, Asset, asset_ids, "asset")
        for link in session.exec(select(RiskAsset).where(RiskAsset.risk_id == risk.id)):
            session.delete(link)
        session.flush()
        for asset in assets:
            session.add(RiskAsset(risk_id=risk.id, asset_id=asset.id))
        changed["asset_ids"] = [a.id for a in assets]
    if obligation_ids is not None:
        obligations = require_ids(session, Obligation, obligation_ids, "obligation")
        for link in session.exec(select(RiskObligation).where(RiskObligation.risk_id == risk.id)):
            session.delete(link)
        session.flush()
        for obligation in obligations:
            session.add(RiskObligation(risk_id=risk.id, obligation_id=obligation.id))
        changed["obligation_ids"] = [o.id for o in obligations]
    return changed


def linked_ids(session: Session, risk_id: int) -> dict[str, list[int]]:
    return {
        "asset_ids": list(
            session.exec(select(RiskAsset.asset_id).where(RiskAsset.risk_id == risk_id))
        ),
        "obligation_ids": list(
            session.exec(
                select(RiskObligation.obligation_id).where(RiskObligation.risk_id == risk_id)
            )
        ),
    }


# ── Assessments ────────────────────────────────────────────────────────────────────────────


def assessments_of(session: Session, risk_id: int) -> list[RiskAssessment]:
    return list(
        session.exec(
            select(RiskAssessment)
            .where(RiskAssessment.risk_id == risk_id)
            .order_by(col(RiskAssessment.id))
        )
    )


def record_assessment(
    session: Session,
    by: audit.AuditActor,
    risk: Risk,
    *,
    likelihood: int,
    impact: int,
    rationale: str,
    assessment_type: AssessmentType,
    assessed_on: date | None = None,
) -> tuple[RiskAssessment, ScoreResult]:
    """Score with the current policy and store a new, permanent assessment row."""
    has_initial = (
        session.exec(
            select(RiskAssessment.id).where(
                RiskAssessment.risk_id == risk.id,
                RiskAssessment.assessment_type == AssessmentType.INITIAL.value,
            )
        ).first()
        is not None
    )
    if assessment_type == AssessmentType.INITIAL and has_initial:
        raise RegisterError(
            "This risk already has its initial assessment; record a reassessment instead.", 409
        )
    if assessment_type == AssessmentType.REASSESSMENT and not has_initial:
        raise RegisterError("Record the initial assessment before any reassessment.", 409)
    if not rationale or not rationale.strip():
        raise RegisterError("A rationale is required for every assessment.")

    current_policy = governance.policy(session)
    result = score_risk(likelihood, impact, current_policy)
    row = RiskAssessment(
        risk_id=risk.id,  # type: ignore[arg-type]
        assessment_type=assessment_type.value,
        likelihood=result.likelihood,
        impact=result.impact,
        score=result.score,
        band=result.band.value,
        above_appetite=result.above_appetite,
        appetite_threshold=result.appetite_threshold,
        rationale=rationale.strip(),
        assessed_by_id=by.user_id,  # type: ignore[arg-type]
    )
    session.add(row)
    before_review = risk.next_review_date
    risk.next_review_date = next_review(
        result.band, assessed_on or governance.org_today(session), current_policy
    )
    session.add(risk)
    session.flush()
    audit.record(
        session,
        AuditAction.ASSESS,
        by,
        object_type="risk",
        object_id=risk.id,
        before={"next_review_date": before_review},
        after={
            "assessment_id": row.id,
            "type": row.assessment_type,
            "likelihood": likelihood,
            "impact": impact,
            "score": result.score,
            "band": result.band.value,
            "above_appetite": result.above_appetite,
            "next_review_date": risk.next_review_date,
        },
        detail=result.explanation,
    )
    return row, result
