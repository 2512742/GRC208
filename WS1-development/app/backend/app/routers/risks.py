"""Risks and their assessments (brief features 1, 2, 4).

There are deliberately no routes to edit or delete an assessment (test T11): a new score is a
new row. Reassessment (which needs evidence) is added with the evidence routes in P5.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.core.auth import AuthContext, deny, ensure, get_auth
from app.core.permissions import Perm, Target, authorize
from app.db import get_session
from app.models import Risk
from app.models.enums import AssessmentType, AuditAction, Band, RiskStatus
from app.schemas.register import (
    OWNER_EDITABLE,
    AssessmentCreate,
    Page,
    RiskCreate,
    RiskDetail,
    RiskSummary,
    RiskUpdate,
)
from app.services import audit, risk_views
from app.services import register as reg
from app.services.clock import now_utc

router = APIRouter(prefix="/risks", tags=["risks"])


def _fail(exc: reg.RegisterError) -> HTTPException:
    return HTTPException(exc.status, str(exc))


def _get_risk(db: Session, risk_id: int) -> Risk:
    risk = db.get(Risk, risk_id)
    if risk is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Risk not found.")
    return risk


@router.get("", response_model=Page[RiskSummary])
def list_risks(
    q: str | None = Query(default=None, max_length=100, description="Search code, title, threat"),
    service_id: int | None = None,
    owner_id: int | None = None,
    obligation_id: int | None = None,
    band: Band | None = None,
    risk_status: RiskStatus | None = Query(default=None, alias="status"),
    above_appetite: bool | None = None,
    unassessed: bool | None = None,
    sort: str = Query(default="score", pattern="^(score|code|review)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    _: AuthContext = Depends(get_auth),
    db: Session = Depends(get_session),
) -> Page[RiskSummary]:
    filters = risk_views.RiskFilters(
        q=q,
        service_id=service_id,
        owner_id=owner_id,
        obligation_id=obligation_id,
        band=band,
        status=risk_status,
        above_appetite=above_appetite,
        unassessed=unassessed,
    )
    items, total = risk_views.list_risks(db, filters, page=page, page_size=page_size, sort=sort)
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/{risk_id}", response_model=RiskDetail)
def get_risk(
    risk_id: int, _: AuthContext = Depends(get_auth), db: Session = Depends(get_session)
) -> RiskDetail:
    return risk_views.risk_detail(db, _get_risk(db, risk_id))


@router.post("", response_model=RiskDetail, status_code=status.HTTP_201_CREATED)
def create_risk(
    body: RiskCreate, ctx: AuthContext = Depends(get_auth), db: Session = Depends(get_session)
) -> RiskDetail:
    ensure(db, ctx, Perm.CREATE_RISK, object_type="risk")
    if body.initial_assessment is not None:
        ensure(db, ctx, Perm.ASSESS_RISK, object_type="risk")
    values = body.model_dump(exclude={"initial_assessment"})
    try:
        risk = reg.create_risk(db, ctx.audit_actor, **values)
        if body.initial_assessment is not None:
            reg.record_assessment(
                db,
                ctx.audit_actor,
                risk,
                **body.initial_assessment.model_dump(),
                assessment_type=AssessmentType.INITIAL,
            )
    except reg.RegisterError as exc:
        db.rollback()
        raise _fail(exc) from exc
    db.commit()
    return risk_views.risk_detail(db, risk)


@router.patch("/{risk_id}", response_model=RiskDetail)
def update_risk(
    risk_id: int,
    body: RiskUpdate,
    ctx: AuthContext = Depends(get_auth),
    db: Session = Depends(get_session),
) -> RiskDetail:
    risk = _get_risk(db, risk_id)
    changes = body.model_dump(exclude_unset=True)
    target = Target(risk_owner_id=risk.owner_id)

    if not authorize(ctx.actor, Perm.EDIT_RISK, target):
        # Not an analyst: allowed only as this risk's owner, and only the limited fields.
        ensure(db, ctx, Perm.EDIT_OWN_RISK_LIMITED, target, object_type="risk", object_id=risk.id)
        restricted = sorted(set(changes) - OWNER_EDITABLE)
        if restricted:
            deny(
                db,
                ctx,
                "As risk owner you can change only the description and the next "
                f"review date (not: {', '.join(restricted)}).",
                object_type="risk",
                object_id=risk.id,
            )

    asset_ids = changes.pop("asset_ids", None)
    obligation_ids = changes.pop("obligation_ids", None)
    before = {**reg.snapshot(risk, reg.RISK_FIELDS), **reg.linked_ids(db, risk.id)}  # type: ignore[arg-type]
    try:
        if "owner_id" in changes:
            reg.check_risk_owner(db, changes["owner_id"])
        for field, value in changes.items():
            setattr(risk, field, value)
        links = reg.set_links(db, risk, asset_ids=asset_ids, obligation_ids=obligation_ids)
    except reg.RegisterError as exc:
        db.rollback()
        raise _fail(exc) from exc
    risk.updated_at = now_utc()
    db.add(risk)
    after = {**reg.snapshot(risk, reg.RISK_FIELDS), **reg.linked_ids(db, risk.id), **links}  # type: ignore[arg-type]
    audit.record(
        db,
        AuditAction.UPDATE,
        ctx.audit_actor,
        object_type="risk",
        object_id=risk.id,
        before={k: v for k, v in before.items() if before.get(k) != after.get(k)},
        after={k: v for k, v in after.items() if before.get(k) != after.get(k)},
    )
    db.commit()
    return risk_views.risk_detail(db, risk)


@router.post(
    "/{risk_id}/assessments", response_model=RiskDetail, status_code=status.HTTP_201_CREATED
)
def add_initial_assessment(
    risk_id: int,
    body: AssessmentCreate,
    ctx: AuthContext = Depends(get_auth),
    db: Session = Depends(get_session),
) -> RiskDetail:
    """Record the risk's initial assessment. (Reassessments, which require evidence, use
    the reassessment route added in P5.)"""
    risk = _get_risk(db, risk_id)
    ensure(
        db,
        ctx,
        Perm.ASSESS_RISK,
        Target(risk_owner_id=risk.owner_id),
        object_type="risk",
        object_id=risk.id,
    )
    try:
        reg.record_assessment(
            db, ctx.audit_actor, risk, **body.model_dump(), assessment_type=AssessmentType.INITIAL
        )
    except reg.RegisterError as exc:
        db.rollback()
        raise _fail(exc) from exc
    db.commit()
    return risk_views.risk_detail(db, risk)
