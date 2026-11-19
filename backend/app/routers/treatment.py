"""Treatment decisions, actions, reassessment and acceptance routes (brief features 3-5)."""

from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlmodel import Session, col, func, select

from app.core.auth import AuthContext, deny, ensure, get_auth
from app.core.permissions import Actor, Perm, Target, authorize
from app.db import get_session
from app.models import (
    AcceptanceRequest,
    ActionControl,
    Control,
    Evidence,
    Risk,
    RiskAssessment,
    TreatmentAction,
    TreatmentDecision,
    User,
)
from app.models.enums import AcceptanceStatus, ActionStatus, Band, EvidenceTarget
from app.models.records import EVIDENCE_MAX_BYTES
from app.routers.evidence import evidence_out, read_upload
from app.schemas.register import PersonRef, ScoreSummary
from app.schemas.treatment import (
    AcceptanceCreate,
    AcceptanceDecision,
    AcceptanceOut,
    ActionCreate,
    ActionOut,
    ActionUpdate,
    ControlRef,
    DecisionCreate,
    DecisionOut,
    ReassessmentOut,
)
from app.services import governance
from app.services import treatment as tr
from app.services.evidence import EvidenceRejected, check_evidence
from app.services.scoring import GovernancePolicy, score_risk
from app.services.workflow import OPEN_ACTION_STATUSES, acceptance_is_expired, action_is_overdue

router = APIRouter(tags=["treatment"])


def _fail(exc: tr.TreatmentError | EvidenceRejected) -> HTTPException:
    return HTTPException(getattr(exc, "status", 422), str(exc))


def _risk(db: Session, risk_id: int) -> Risk:
    risk = db.get(Risk, risk_id)
    if risk is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Risk not found.")
    return risk


def _people(db: Session, ids: set[int | None]) -> dict[int, PersonRef]:
    wanted = {i for i in ids if i is not None}
    return {
        u.id: PersonRef.model_validate(u)  # type: ignore[misc]
        for u in db.exec(select(User).where(col(User.id).in_(wanted)))
    }


def _risk_ref(risk: Risk) -> dict[str, object]:
    return {
        "id": risk.id,
        "risk_code": risk.risk_code,
        "title": risk.title,
        "owner_id": risk.owner_id,
        "status": risk.status,
    }


# ── Decisions ──────────────────────────────────────────────────────────────────────────────


def _decision_out(row: TreatmentDecision, people: dict[int, PersonRef]) -> DecisionOut:
    target = (
        row.target_likelihood * row.target_impact
        if row.target_likelihood and row.target_impact
        else None
    )
    return DecisionOut(
        id=row.id,
        strategy=row.strategy,
        justification=row.justification,  # type: ignore[arg-type]
        target_likelihood=row.target_likelihood,
        target_impact=row.target_impact,
        target_score=target,
        decided_by=people[row.decided_by_id],
        decided_at=row.decided_at,
    )


@router.get("/risks/{risk_id}/decisions", response_model=list[DecisionOut])
def list_decisions(
    risk_id: int, _: AuthContext = Depends(get_auth), db: Session = Depends(get_session)
) -> list[DecisionOut]:
    _risk(db, risk_id)
    rows = list(
        db.exec(
            select(TreatmentDecision)
            .where(TreatmentDecision.risk_id == risk_id)
            .order_by(col(TreatmentDecision.id))
        )
    )
    people = _people(db, {r.decided_by_id for r in rows})
    return [_decision_out(r, people) for r in rows]


@router.post(
    "/risks/{risk_id}/decisions", response_model=DecisionOut, status_code=status.HTTP_201_CREATED
)
def add_decision(
    risk_id: int,
    body: DecisionCreate,
    ctx: AuthContext = Depends(get_auth),
    db: Session = Depends(get_session),
) -> DecisionOut:
    risk = _risk(db, risk_id)
    ensure(
        db,
        ctx,
        Perm.DECIDE_TREATMENT,
        Target(risk_owner_id=risk.owner_id),
        object_type="risk",
        object_id=risk.id,
    )
    try:
        row = tr.decide_treatment(db, ctx.audit_actor, risk, **body.model_dump())
    except tr.TreatmentError as exc:
        db.rollback()
        raise _fail(exc) from exc
    db.commit()
    return _decision_out(row, _people(db, {row.decided_by_id}))


# ── Actions ────────────────────────────────────────────────────────────────────────────────


def _actions_out(db: Session, actor: Actor, actions: list[TreatmentAction]) -> list[ActionOut]:
    if not actions:
        return []
    ids = [a.id for a in actions]
    today = governance.org_today(db)
    risks = {
        r.id: r for r in db.exec(select(Risk).where(col(Risk.id).in_({a.risk_id for a in actions})))
    }
    people = _people(db, {a.owner_id for a in actions} | {a.completed_by_id for a in actions})
    controls: dict[int, list[ControlRef]] = defaultdict(list)
    for action_id, control in db.exec(
        select(ActionControl.action_id, Control)
        .join(Control, Control.id == ActionControl.control_id)
        .where(col(ActionControl.action_id).in_(ids))
        .order_by(col(Control.framework), col(Control.id))
    ):
        controls[action_id].append(
            ControlRef(
                id=control.id,
                framework=control.framework,  # type: ignore[arg-type]
                control_ref=control.control_ref,
                short_title=control.short_title,
            )
        )
    evidence_counts = dict(
        db.exec(
            select(Evidence.target_id, func.count())
            .where(
                Evidence.target_type == EvidenceTarget.ACTION.value,
                col(Evidence.target_id).in_(ids),
            )
            .group_by(Evidence.target_id)
        ).all()
    )
    out = []
    for a in actions:
        risk = risks[a.risk_id]
        overdue = action_is_overdue(a.status, a.due_date, today)
        target = Target(risk_owner_id=risk.owner_id, action_owner_id=a.owner_id)
        out.append(
            ActionOut(
                id=a.id,
                action_code=a.action_code,
                risk=_risk_ref(risk),
                title=a.title,  # type: ignore[arg-type]
                description=a.description,
                owner=people[a.owner_id],
                due_date=a.due_date,
                status=a.status,
                overdue=overdue,  # type: ignore[arg-type]
                days_overdue=(today - a.due_date).days if overdue else 0,
                estimated_cost_ngn=a.estimated_cost_ngn,
                controls=controls.get(a.id, []),  # type: ignore[arg-type]
                completed_at=a.completed_at,
                completed_by=people.get(a.completed_by_id) if a.completed_by_id else None,  # type: ignore[arg-type]
                completion_note=a.completion_note,
                evidence_count=evidence_counts.get(a.id, 0),
                can_update=a.status in OPEN_ACTION_STATUSES
                and bool(authorize(actor, Perm.UPDATE_ACTION, target)),
                created_at=a.created_at,
            )
        )
    return out


def _action(db: Session, action_id: int) -> TreatmentAction:
    action = db.get(TreatmentAction, action_id)
    if action is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Action not found.")
    return action


@router.get("/actions", response_model=list[ActionOut])
def list_actions(
    mine: bool = False,
    overdue: bool | None = None,
    action_status: ActionStatus | None = Query(default=None, alias="status"),
    risk_id: int | None = None,
    owner_id: int | None = None,
    ctx: AuthContext = Depends(get_auth),
    db: Session = Depends(get_session),
) -> list[ActionOut]:
    """Overdue first, then by due date."""
    query = select(TreatmentAction)
    if mine:
        query = query.where(TreatmentAction.owner_id == ctx.user.id)
    if owner_id is not None:
        query = query.where(TreatmentAction.owner_id == owner_id)
    if action_status is not None:
        query = query.where(TreatmentAction.status == action_status.value)
    if risk_id is not None:
        query = query.where(TreatmentAction.risk_id == risk_id)
    if overdue is not None:
        today = governance.org_today(db)
        is_overdue = col(TreatmentAction.status).in_(OPEN_ACTION_STATUSES) & (
            col(TreatmentAction.due_date) < today
        )
        query = query.where(is_overdue if overdue else ~is_overdue)
    rows = list(db.exec(query.order_by(col(TreatmentAction.due_date), col(TreatmentAction.id))))
    out = _actions_out(db, ctx.actor, rows)
    return sorted(out, key=lambda a: (not a.overdue, a.status not in OPEN_ACTION_STATUSES))


@router.get("/risks/{risk_id}/actions", response_model=list[ActionOut])
def risk_actions(
    risk_id: int, ctx: AuthContext = Depends(get_auth), db: Session = Depends(get_session)
) -> list[ActionOut]:
    _risk(db, risk_id)
    rows = list(
        db.exec(
            select(TreatmentAction)
            .where(TreatmentAction.risk_id == risk_id)
            .order_by(col(TreatmentAction.id))
        )
    )
    return _actions_out(db, ctx.actor, rows)


@router.get("/actions/{action_id}", response_model=ActionOut)
def get_action(
    action_id: int, ctx: AuthContext = Depends(get_auth), db: Session = Depends(get_session)
) -> ActionOut:
    return _actions_out(db, ctx.actor, [_action(db, action_id)])[0]


@router.post(
    "/risks/{risk_id}/actions", response_model=ActionOut, status_code=status.HTTP_201_CREATED
)
def add_action(
    risk_id: int,
    body: ActionCreate,
    ctx: AuthContext = Depends(get_auth),
    db: Session = Depends(get_session),
) -> ActionOut:
    risk = _risk(db, risk_id)
    ensure(
        db,
        ctx,
        Perm.CREATE_ACTION,
        Target(risk_owner_id=risk.owner_id),
        object_type="risk",
        object_id=risk.id,
    )
    try:
        action = tr.create_action(db, ctx.audit_actor, risk, **body.model_dump())
    except tr.TreatmentError as exc:
        db.rollback()
        raise _fail(exc) from exc
    db.commit()
    return _actions_out(db, ctx.actor, [action])[0]


PLANNING_FIELDS = frozenset({"title", "owner_id", "due_date", "estimated_cost_ngn", "control_ids"})


@router.patch("/actions/{action_id}", response_model=ActionOut)
def change_action(
    action_id: int,
    body: ActionUpdate,
    ctx: AuthContext = Depends(get_auth),
    db: Session = Depends(get_session),
) -> ActionOut:
    action = _action(db, action_id)
    risk = _risk(db, action.risk_id)
    ensure(
        db,
        ctx,
        Perm.UPDATE_ACTION,
        Target(risk_owner_id=risk.owner_id, action_owner_id=action.owner_id),
        object_type="action",
        object_id=action.id,
    )
    changes = body.model_dump(exclude_unset=True)
    planning = sorted(PLANNING_FIELDS & set(changes))
    if planning and not authorize(
        ctx.actor, Perm.CREATE_ACTION, Target(risk_owner_id=risk.owner_id)
    ):
        deny(
            db,
            ctx,
            f"Only the risk owner or an analyst can change an action's {', '.join(planning)}.",
            object_type="action",
            object_id=action.id,
        )
    control_ids = changes.pop("control_ids", None)
    try:
        tr.update_action(db, ctx.audit_actor, action, changes)
        if control_ids is not None:
            tr.link_controls(db, action, control_ids)
    except (tr.TreatmentError, ValueError) as exc:
        db.rollback()
        raise HTTPException(getattr(exc, "status", 422), str(exc)) from exc
    db.commit()
    return _actions_out(db, ctx.actor, [action])[0]


@router.post("/actions/{action_id}/complete", response_model=ActionOut)
def complete_action(
    action_id: int,
    note: str = Form(min_length=10, max_length=5000, description="What was done"),
    file: UploadFile = File(description=f"Evidence (max {EVIDENCE_MAX_BYTES // 1_048_576} MB)"),
    ctx: AuthContext = Depends(get_auth),
    db: Session = Depends(get_session),
) -> ActionOut:
    """Complete with evidence. The risk score does not change: the risk moves to
    'awaiting reassessment' (brief feature 4, test T08)."""
    action = _action(db, action_id)
    risk = _risk(db, action.risk_id)
    ensure(
        db,
        ctx,
        Perm.UPDATE_ACTION,
        Target(risk_owner_id=risk.owner_id, action_owner_id=action.owner_id),
        object_type="action",
        object_id=action.id,
    )
    try:
        content = read_upload(file)
        checked = check_evidence(file.filename or "", content)
        tr.complete_action(
            db, ctx.audit_actor, action, note=note, evidence=checked, content=content
        )
    except (tr.TreatmentError, EvidenceRejected) as exc:
        db.rollback()
        raise _fail(exc) from exc
    except ValueError as exc:  # invalid transition (already completed or cancelled)
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    db.commit()
    return _actions_out(db, ctx.actor, [action])[0]


# ── Reassessment ───────────────────────────────────────────────────────────────────────────


@router.post(
    "/risks/{risk_id}/reassessments",
    response_model=ReassessmentOut,
    status_code=status.HTTP_201_CREATED,
)
def reassess(
    risk_id: int,
    likelihood: int = Form(ge=1, le=5),
    impact: int = Form(ge=1, le=5),
    rationale: str = Form(min_length=10, max_length=5000),
    close_risk: bool = Form(default=False),
    file: UploadFile = File(description="Evidence supporting the new scores"),
    ctx: AuthContext = Depends(get_auth),
    db: Session = Depends(get_session),
) -> ReassessmentOut:
    """A documented residual reassessment supported by evidence (brief feature 4, T09/T10).
    Adds a new assessment row; the original stays."""
    risk = _risk(db, risk_id)
    ensure(
        db,
        ctx,
        Perm.ASSESS_RISK,
        Target(risk_owner_id=risk.owner_id),
        object_type="risk",
        object_id=risk.id,
    )
    try:
        content = read_upload(file)
        checked = check_evidence(file.filename or "", content)
        row, result, stored = tr.reassess(
            db,
            ctx.audit_actor,
            risk,
            likelihood=likelihood,
            impact=impact,
            rationale=rationale,
            evidence=checked,
            content=content,
            close_risk=close_risk,
        )
    except (tr.TreatmentError, EvidenceRejected) as exc:
        db.rollback()
        raise _fail(exc) from exc
    db.commit()
    original = db.exec(
        select(RiskAssessment.score).where(
            RiskAssessment.risk_id == risk.id, RiskAssessment.assessment_type == "initial"
        )
    ).first()
    return ReassessmentOut(
        assessment_id=row.id,
        score=result.score,
        band=result.band.value,  # type: ignore[arg-type]
        above_appetite=result.above_appetite,
        explanation=result.explanation,
        original_score=original,
        risk_status=risk.status,
        evidence=evidence_out(db, stored),
    )


# ── Acceptance ─────────────────────────────────────────────────────────────────────────────


def _acceptances_out(
    db: Session, actor: Actor, rows: list[AcceptanceRequest]
) -> list[AcceptanceOut]:
    if not rows:
        return []
    today = governance.org_today(db)
    risks = {
        r.id: r for r in db.exec(select(Risk).where(col(Risk.id).in_({a.risk_id for a in rows})))
    }
    people = _people(db, {a.requested_by_id for a in rows} | {a.decided_by_id for a in rows})
    out = []
    for a in rows:
        risk = risks[a.risk_id]
        current = tr.current_assessment(db, risk.id)  # type: ignore[arg-type]
        score = None
        if current is not None:
            result = score_risk(
                current.likelihood,
                current.impact,
                GovernancePolicy(appetite_threshold=current.appetite_threshold),
            )
            score = ScoreSummary(
                likelihood=current.likelihood,
                impact=current.impact,
                score=current.score,
                band=Band(current.band),
                above_appetite=current.above_appetite,
                explanation=result.explanation,
            )
        decision = authorize(
            actor,
            Perm.DECIDE_ACCEPTANCE,
            Target(risk_owner_id=risk.owner_id, acceptance_requested_by_id=a.requested_by_id),
        )
        pending = a.status == AcceptanceStatus.PENDING.value
        if not pending:
            reason: str | None = f"Already {a.status}."
        elif not decision.allowed:
            reason = decision.reason
        else:
            reason = None
        out.append(
            AcceptanceOut(
                id=a.id,
                risk=_risk_ref(risk),
                current=score,  # type: ignore[arg-type]
                requested_by=people[a.requested_by_id],
                requested_at=a.requested_at,
                justification=a.justification,
                proposed_expiry=a.proposed_expiry,
                status=a.status,  # type: ignore[arg-type]
                expired=acceptance_is_expired(a.status, a.expiry_date, today),
                decided_by=people.get(a.decided_by_id) if a.decided_by_id else None,  # type: ignore[arg-type]
                decision_date=a.decision_date,
                decision_comment=a.decision_comment,
                expiry_date=a.expiry_date,
                can_decide=reason is None,
                cannot_decide_reason=reason,
            )
        )
    return out


@router.get("/acceptances", response_model=list[AcceptanceOut])
def list_acceptances(
    acceptance_status: AcceptanceStatus | None = Query(default=None, alias="status"),
    risk_id: int | None = None,
    expired: bool | None = None,
    ctx: AuthContext = Depends(get_auth),
    db: Session = Depends(get_session),
) -> list[AcceptanceOut]:
    query = select(AcceptanceRequest).order_by(col(AcceptanceRequest.id).desc())
    if acceptance_status is not None:
        query = query.where(AcceptanceRequest.status == acceptance_status.value)
    if risk_id is not None:
        query = query.where(AcceptanceRequest.risk_id == risk_id)
    out = _acceptances_out(db, ctx.actor, list(db.exec(query)))
    return [a for a in out if expired is None or a.expired == expired]


@router.get("/acceptances/{acceptance_id}", response_model=AcceptanceOut)
def get_acceptance(
    acceptance_id: int, ctx: AuthContext = Depends(get_auth), db: Session = Depends(get_session)
) -> AcceptanceOut:
    row = db.get(AcceptanceRequest, acceptance_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Acceptance request not found.")
    return _acceptances_out(db, ctx.actor, [row])[0]


@router.post(
    "/risks/{risk_id}/acceptances",
    response_model=AcceptanceOut,
    status_code=status.HTTP_201_CREATED,
)
def request_acceptance(
    risk_id: int,
    body: AcceptanceCreate,
    ctx: AuthContext = Depends(get_auth),
    db: Session = Depends(get_session),
) -> AcceptanceOut:
    risk = _risk(db, risk_id)
    ensure(
        db,
        ctx,
        Perm.REQUEST_ACCEPTANCE,
        Target(risk_owner_id=risk.owner_id),
        object_type="risk",
        object_id=risk.id,
    )
    try:
        row = tr.request_acceptance(db, ctx.audit_actor, risk, **body.model_dump())
    except tr.TreatmentError as exc:
        db.rollback()
        raise _fail(exc) from exc
    db.commit()
    return _acceptances_out(db, ctx.actor, [row])[0]


@router.post("/acceptances/{acceptance_id}/decision", response_model=AcceptanceOut)
def decide_acceptance(
    acceptance_id: int,
    body: AcceptanceDecision,
    ctx: AuthContext = Depends(get_auth),
    db: Session = Depends(get_session),
) -> AcceptanceOut:
    """Approve or reject. Refused (403, audited) for anyone who isn't an approver, and for an
    approver who owns the risk or made the request (tests T12, T14, T20)."""
    row = db.get(AcceptanceRequest, acceptance_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Acceptance request not found.")
    risk = _risk(db, row.risk_id)
    ensure(
        db,
        ctx,
        Perm.DECIDE_ACCEPTANCE,
        Target(risk_owner_id=risk.owner_id, acceptance_requested_by_id=row.requested_by_id),
        object_type="acceptance",
        object_id=row.id,
    )
    try:
        tr.decide_acceptance(
            db,
            ctx.audit_actor,
            row,
            approve=body.decision == "approve",
            comment=body.comment,
            expiry_date=body.expiry_date,
        )
    except tr.TreatmentError as exc:
        db.rollback()
        raise _fail(exc) from exc
    db.commit()
    return _acceptances_out(db, ctx.actor, [row])[0]
