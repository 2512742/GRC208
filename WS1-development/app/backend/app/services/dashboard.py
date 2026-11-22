"""Dashboard and management-report figures (brief feature 6).

One read model feeds the dashboard, the management report page and its CSV/PDF exports, so
the numbers on screen and on paper always agree (test T17/T18).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field
from sqlmodel import Session, col, select

from app.models import (
    AcceptanceRequest,
    Asset,
    BusinessService,
    Obligation,
    RiskAssessment,
    RiskAsset,
    RiskObligation,
    TreatmentAction,
    User,
)
from app.models.enums import AcceptanceStatus, AssessmentType, Band, RiskStatus
from app.schemas.register import RiskSummary
from app.services import governance, risk_views
from app.services.workflow import OPEN_ACTION_STATUSES, acceptance_is_expired, action_is_overdue

BANDS = [Band.LOW.value, Band.MEDIUM.value, Band.HIGH.value, Band.CRITICAL.value]


class HeatCell(BaseModel):
    likelihood: int
    impact: int
    score: int
    count: int
    risk_codes: list[str]


class OverdueAction(BaseModel):
    action_id: int
    action_code: str
    title: str
    risk_code: str
    owner: str
    due_date: date
    days_overdue: int


class AcceptanceLine(BaseModel):
    acceptance_id: int
    risk_code: str
    risk_title: str
    status: str
    requested_by: str
    decided_by: str | None
    expiry_date: date | None
    expired: bool


class Overview(BaseModel):
    generated_for: date
    appetite_threshold: int
    totals: dict[str, int]
    by_band: dict[str, int]
    by_status: dict[str, int]
    by_service: list[dict[str, object]]
    regulatory_exposure: list[dict[str, object]]
    heat_map_current: list[HeatCell]
    heat_map_original: list[HeatCell]
    above_appetite: list[RiskSummary]
    overdue_actions: list[OverdueAction]
    upcoming_reviews: list[RiskSummary]
    acceptances: list[AcceptanceLine]
    open_treatment_cost_ngn: Decimal
    risks: list[RiskSummary] = Field(default_factory=list)


def _all_summaries(session: Session, filters: risk_views.RiskFilters) -> list[RiskSummary]:
    items, _ = risk_views.list_risks(session, filters, page=1, page_size=10_000)
    return items


def _heat_map(
    risks: list[RiskSummary], original_scores: dict[int, tuple[int, int]], use_original: bool
) -> list[HeatCell]:
    cells: dict[tuple[int, int], list[str]] = defaultdict(list)
    for risk in risks:
        if use_original:
            point = original_scores.get(risk.id)
        else:
            point = (risk.current.likelihood, risk.current.impact) if risk.current else None
        if point:
            cells[point].append(risk.risk_code)
    return [
        HeatCell(
            likelihood=lk,
            impact=im,
            score=lk * im,
            count=len(cells[(lk, im)]),
            risk_codes=sorted(cells[(lk, im)]),
        )
        for lk in range(5, 0, -1)
        for im in range(1, 6)
    ]


def overview(session: Session, filters: risk_views.RiskFilters | None = None) -> Overview:
    filters = filters or risk_views.RiskFilters()
    policy = governance.policy(session)
    today = governance.org_today(session)
    risks = _all_summaries(session, filters)
    risk_ids = [r.id for r in risks]
    codes = {r.id: r.risk_code for r in risks}

    originals = {
        rid: (lk, im)
        for rid, lk, im in session.exec(
            select(RiskAssessment.risk_id, RiskAssessment.likelihood, RiskAssessment.impact).where(
                col(RiskAssessment.risk_id).in_(risk_ids),
                RiskAssessment.assessment_type == AssessmentType.INITIAL.value,
            )
        )
    }

    # Actions on the risks in scope.
    actions = list(
        session.exec(select(TreatmentAction).where(col(TreatmentAction.risk_id).in_(risk_ids)))
    )
    owners = {u.id: u.full_name for u in session.exec(select(User))}
    overdue = sorted(
        (
            OverdueAction(
                action_id=a.id,
                action_code=a.action_code,
                title=a.title,  # type: ignore[arg-type]
                risk_code=codes[a.risk_id],
                owner=owners.get(a.owner_id, "?"),
                due_date=a.due_date,
                days_overdue=(today - a.due_date).days,
            )
            for a in actions
            if action_is_overdue(a.status, a.due_date, today)
        ),
        key=lambda o: -o.days_overdue,
    )
    open_cost = sum(
        (a.estimated_cost_ngn or Decimal(0) for a in actions if a.status in OPEN_ACTION_STATUSES),
        Decimal(0),
    )

    # Acceptances on the risks in scope: pending, approved (valid or expired).
    acceptances = []
    for a in session.exec(
        select(AcceptanceRequest)
        .where(
            col(AcceptanceRequest.risk_id).in_(risk_ids),
            col(AcceptanceRequest.status).in_(
                [AcceptanceStatus.PENDING.value, AcceptanceStatus.APPROVED.value]
            ),
        )
        .order_by(col(AcceptanceRequest.id))
    ):
        risk = next(r for r in risks if r.id == a.risk_id)
        acceptances.append(
            AcceptanceLine(
                acceptance_id=a.id,
                risk_code=risk.risk_code,
                risk_title=risk.title,  # type: ignore[arg-type]
                status=a.status,
                requested_by=owners.get(a.requested_by_id, "?"),
                decided_by=owners.get(a.decided_by_id) if a.decided_by_id else None,
                expiry_date=a.expiry_date,
                expired=acceptance_is_expired(a.status, a.expiry_date, today),
            )
        )

    # Services and regulatory exposure.
    service_names = {s.id: (s.code, s.name) for s in session.exec(select(BusinessService))}
    risk_services: dict[int, set[int]] = defaultdict(set)
    for risk_id, service_id in session.exec(
        select(RiskAsset.risk_id, Asset.service_id)
        .join(Asset, Asset.id == RiskAsset.asset_id)
        .where(col(RiskAsset.risk_id).in_(risk_ids))
    ):
        risk_services[risk_id].add(service_id)
    by_service = []
    for service_id, (code, name) in sorted(service_names.items(), key=lambda kv: kv[1][0]):
        in_service = [r for r in risks if service_id in risk_services.get(r.id, set())]
        by_service.append(
            {
                "service_id": service_id,
                "code": code,
                "name": name,
                "risks": len(in_service),
                "above_appetite": sum(
                    1 for r in in_service if r.current and r.current.above_appetite
                ),
                "highest_score": max(
                    (r.current.score for r in in_service if r.current), default=None
                ),
            }
        )
    regimes: dict[str, set[int]] = defaultdict(set)
    for risk_id, regime in session.exec(
        select(RiskObligation.risk_id, Obligation.regime)
        .join(Obligation, Obligation.id == RiskObligation.obligation_id)
        .where(col(RiskObligation.risk_id).in_(risk_ids))
    ):
        regimes[regime].add(risk_id)
    above_ids = {r.id for r in risks if r.current and r.current.above_appetite}
    exposure = [
        {"regime": regime, "risks": len(ids), "above_appetite": len(ids & above_ids)}
        for regime, ids in sorted(regimes.items())
    ]

    scored = [r for r in risks if r.current]
    upcoming = sorted(
        (r for r in risks if r.review_due_soon and r.status != RiskStatus.CLOSED),
        key=lambda r: (r.next_review_date or date.max, r.risk_code),
    )
    by_band = Counter(r.current.band.value for r in scored)
    return Overview(
        generated_for=today,
        appetite_threshold=policy.appetite_threshold,
        totals={
            "risks": len(risks),
            "assessed": len(scored),
            "above_appetite": len(above_ids),
            "open_actions": sum(1 for a in actions if a.status in OPEN_ACTION_STATUSES),
            "overdue_actions": len(overdue),
            "pending_acceptances": sum(1 for a in acceptances if a.status == "pending"),
            "expired_acceptances": sum(1 for a in acceptances if a.expired),
            "awaiting_reassessment": sum(1 for r in risks if r.status == "awaiting_reassessment"),
            "reviews_due": len(upcoming),
        },
        by_band={band: by_band.get(band, 0) for band in BANDS},
        by_status=dict(Counter(r.display_status for r in risks)),
        by_service=by_service,
        regulatory_exposure=exposure,
        heat_map_current=_heat_map(risks, originals, use_original=False),
        heat_map_original=_heat_map(risks, originals, use_original=True),
        above_appetite=[r for r in risks if r.id in above_ids],
        overdue_actions=overdue,
        upcoming_reviews=upcoming,
        acceptances=acceptances,
        open_treatment_cost_ngn=open_cost,
        risks=risks,
    )
