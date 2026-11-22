"""Read side of the register: risk lists with current/original scores, filters, detail views.

"Current" = the risk's latest assessment row; "original" = its single initial row (PLAN §2.2).
Everything is fetched in a few batched queries, never one query per risk.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from sqlalchemy import and_, exists, func, or_
from sqlalchemy.orm import aliased
from sqlmodel import Session, col, select

from app.models import (
    AcceptanceRequest,
    Asset,
    BusinessService,
    Obligation,
    Risk,
    RiskAssessment,
    RiskAsset,
    RiskObligation,
    TreatmentAction,
    TreatmentDecision,
    User,
)
from app.models.enums import AcceptanceStatus, AssessmentType, Band, RiskStatus
from app.schemas.register import (
    AssessmentOut,
    AssetRef,
    ObligationOut,
    PersonRef,
    RiskDetail,
    RiskSummary,
    ScoreSummary,
)
from app.services import governance
from app.services.scoring import GovernancePolicy, review_is_upcoming, score_risk
from app.services.workflow import (
    OPEN_ACTION_STATUSES,
    acceptance_is_expired,
    display_risk_status,
)

Current = aliased(RiskAssessment, name="current_assessment")


def _latest_ids():  # type: ignore[no-untyped-def]
    return (
        select(RiskAssessment.risk_id, func.max(RiskAssessment.id).label("assessment_id"))
        .group_by(RiskAssessment.risk_id)
        .subquery("latest")
    )


@dataclass
class RiskFilters:
    q: str | None = None
    service_id: int | None = None
    owner_id: int | None = None
    obligation_id: int | None = None
    band: Band | None = None
    status: RiskStatus | None = None
    above_appetite: bool | None = None
    unassessed: bool | None = None


SORTS = {"score", "code", "review"}


def list_risks(
    session: Session, filters: RiskFilters, *, page: int, page_size: int, sort: str = "score"
) -> tuple[list[RiskSummary], int]:
    latest = _latest_ids()
    query = (
        select(Risk, Current)
        .join(latest, latest.c.risk_id == Risk.id, isouter=True)
        .join(Current, Current.id == latest.c.assessment_id, isouter=True)
    )
    conditions = []
    if filters.q:
        needle = f"%{filters.q.strip().lower()}%"
        conditions.append(
            or_(
                *(
                    func.lower(c).like(needle)
                    for c in (
                        Risk.risk_code,
                        Risk.title,
                        Risk.threat,
                        Risk.vulnerability,
                        Risk.description,
                    )
                )
            )
        )
    if filters.service_id is not None:
        conditions.append(
            exists().where(
                RiskAsset.risk_id == Risk.id,
                RiskAsset.asset_id == Asset.id,
                Asset.service_id == filters.service_id,
            )
        )
    if filters.obligation_id is not None:
        conditions.append(
            exists().where(
                RiskObligation.risk_id == Risk.id,
                RiskObligation.obligation_id == filters.obligation_id,
            )
        )
    if filters.owner_id is not None:
        conditions.append(Risk.owner_id == filters.owner_id)
    if filters.status is not None:
        conditions.append(Risk.status == filters.status.value)
    if filters.band is not None:
        conditions.append(Current.band == filters.band.value)
    if filters.above_appetite is not None:
        conditions.append(Current.above_appetite == filters.above_appetite)
    if filters.unassessed is not None:
        conditions.append(
            col(Current.id).is_(None) if filters.unassessed else col(Current.id).is_not(None)
        )
    if conditions:
        query = query.where(and_(*conditions))

    total = session.exec(select(func.count()).select_from(query.subquery())).one()
    order = {
        "score": (func.coalesce(Current.score, 0).desc(), col(Risk.risk_code)),
        "code": (col(Risk.risk_code),),
        "review": (
            col(Risk.next_review_date).is_(None),
            col(Risk.next_review_date),
            col(Risk.risk_code),
        ),
    }[sort if sort in SORTS else "score"]
    rows = session.exec(
        query.order_by(*order).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return build_summaries(session, [(risk, current) for risk, current in rows]), total


def build_summaries(
    session: Session, rows: Sequence[tuple[Risk, RiskAssessment | None]]
) -> list[RiskSummary]:
    if not rows:
        return []
    risk_ids = [risk.id for risk, _ in rows]
    policy = governance.policy(session)
    today = governance.org_today(session)

    owners = _people(session, {risk.owner_id for risk, _ in rows})
    assets_by_risk = _assets_by_risk(session, risk_ids)
    originals = dict(
        session.exec(
            select(RiskAssessment.risk_id, RiskAssessment.score).where(
                col(RiskAssessment.risk_id).in_(risk_ids),
                RiskAssessment.assessment_type == AssessmentType.INITIAL.value,
            )
        ).all()
    )

    treatment = _treatment_state(session, risk_ids, today)

    summaries = []
    for risk, current in rows:
        assets = assets_by_risk.get(risk.id, [])  # type: ignore[arg-type]
        state = treatment.get(risk.id, {})  # type: ignore[arg-type]
        expiry = state.get("acceptance_expiry")
        summaries.append(
            RiskSummary(
                id=risk.id,  # type: ignore[arg-type]
                risk_code=risk.risk_code,
                title=risk.title,
                category=risk.category,
                status=RiskStatus(risk.status),
                owner=owners[risk.owner_id],
                assets=assets,
                services=sorted({a.service_code for a in assets}),
                current=_score_summary(current, policy),
                original_score=originals.get(risk.id),
                next_review_date=risk.next_review_date,
                review_due_soon=review_is_upcoming(risk.next_review_date, today, policy),
                display_status=display_risk_status(
                    risk.status, acceptance_is_expired("approved", expiry, today)
                ),
                strategy=state.get("strategy"),
                open_actions=state.get("open_actions", 0),
                overdue_actions=state.get("overdue_actions", 0),
                acceptance_expiry=expiry,
            )
        )
    return summaries


def _treatment_state(session: Session, risk_ids: list, today: date) -> dict[int, dict]:  # type: ignore[type-arg]
    """Per risk: latest strategy, open/overdue action counts, latest approved acceptance expiry."""
    state: dict[int, dict] = defaultdict(dict)  # type: ignore[type-arg]
    latest_decision = (
        select(TreatmentDecision.risk_id, func.max(TreatmentDecision.id).label("did"))
        .where(col(TreatmentDecision.risk_id).in_(risk_ids))
        .group_by(TreatmentDecision.risk_id)
        .subquery()
    )
    for risk_id, strategy in session.exec(
        select(TreatmentDecision.risk_id, TreatmentDecision.strategy).join(
            latest_decision, latest_decision.c.did == TreatmentDecision.id
        )
    ):
        state[risk_id]["strategy"] = strategy
    for risk_id, due in session.exec(
        select(TreatmentAction.risk_id, TreatmentAction.due_date).where(
            col(TreatmentAction.risk_id).in_(risk_ids),
            col(TreatmentAction.status).in_(OPEN_ACTION_STATUSES),
        )
    ):
        entry = state[risk_id]
        entry["open_actions"] = entry.get("open_actions", 0) + 1
        if due < today:
            entry["overdue_actions"] = entry.get("overdue_actions", 0) + 1
    latest_acceptance = (
        select(AcceptanceRequest.risk_id, func.max(AcceptanceRequest.id).label("aid"))
        .where(
            col(AcceptanceRequest.risk_id).in_(risk_ids),
            AcceptanceRequest.status == AcceptanceStatus.APPROVED.value,
        )
        .group_by(AcceptanceRequest.risk_id)
        .subquery()
    )
    for risk_id, expiry in session.exec(
        select(AcceptanceRequest.risk_id, AcceptanceRequest.expiry_date).join(
            latest_acceptance, latest_acceptance.c.aid == AcceptanceRequest.id
        )
    ):
        state[risk_id]["acceptance_expiry"] = expiry
    return state


def risk_detail(session: Session, risk: Risk) -> RiskDetail:
    history = list(
        session.exec(
            select(RiskAssessment)
            .where(RiskAssessment.risk_id == risk.id)
            .order_by(col(RiskAssessment.id))
        )
    )
    summary = build_summaries(session, [(risk, history[-1] if history else None)])[0]
    people = _people(session, {risk.created_by_id} | {a.assessed_by_id for a in history})
    obligations = session.exec(
        select(Obligation)
        .join(RiskObligation, RiskObligation.obligation_id == Obligation.id)
        .where(RiskObligation.risk_id == risk.id)
        .order_by(col(Obligation.regime), col(Obligation.reference))
    ).all()
    return RiskDetail(
        **summary.model_dump(),
        description=risk.description,
        threat=risk.threat,
        vulnerability=risk.vulnerability,
        business_impact=risk.business_impact,
        obligations=[ObligationOut.model_validate(o) for o in obligations],
        assessments=[assessment_out(a, people[a.assessed_by_id]) for a in history],
        created_by=people[risk.created_by_id],
        created_at=risk.created_at,
        updated_at=risk.updated_at,
    )


def assessment_out(row: RiskAssessment, by: PersonRef) -> AssessmentOut:
    # Re-explain with the threshold in force *at the time* (stored on the row).
    result = score_risk(
        row.likelihood, row.impact, GovernancePolicy(appetite_threshold=row.appetite_threshold)
    )
    return AssessmentOut(
        id=row.id,  # type: ignore[arg-type]
        assessment_type=row.assessment_type,
        likelihood=row.likelihood,
        impact=row.impact,
        score=row.score,
        band=Band(row.band),
        above_appetite=row.above_appetite,
        appetite_threshold=row.appetite_threshold,
        rationale=row.rationale,
        explanation=result.explanation,
        assessed_by=by,
        assessed_at=row.assessed_at,
    )


def _score_summary(row: RiskAssessment | None, policy: GovernancePolicy) -> ScoreSummary | None:
    if row is None:
        return None
    result = score_risk(
        row.likelihood,
        row.impact,
        GovernancePolicy(**{**policy.__dict__, "appetite_threshold": row.appetite_threshold}),
    )
    return ScoreSummary(
        likelihood=row.likelihood,
        impact=row.impact,
        score=row.score,
        band=Band(row.band),
        above_appetite=row.above_appetite,
        explanation=result.explanation,
    )


def _people(session: Session, ids: set[int]) -> dict[int, PersonRef]:
    users = session.exec(select(User).where(col(User.id).in_(ids))).all()
    return {u.id: PersonRef.model_validate(u) for u in users}  # type: ignore[misc]


def _assets_by_risk(session: Session, risk_ids: list[int | None]) -> dict[int, list[AssetRef]]:
    rows = session.exec(
        select(RiskAsset.risk_id, Asset, BusinessService.code)
        .join(Asset, Asset.id == RiskAsset.asset_id)
        .join(BusinessService, BusinessService.id == Asset.service_id)
        .where(col(RiskAsset.risk_id).in_(risk_ids))
        .order_by(col(Asset.asset_code))
    ).all()
    grouped: dict[int, list[AssetRef]] = defaultdict(list)
    for risk_id, asset, service_code in rows:
        grouped[risk_id].append(
            AssetRef(
                id=asset.id, asset_code=asset.asset_code, name=asset.name, service_code=service_code
            )
        )
    return grouped
