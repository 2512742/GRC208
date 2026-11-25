"""Treatment decisions, actions, evidence, reassessment and acceptance (brief features 3-5).

Every function validates, writes and audits inside the caller's transaction; the caller commits.
Permission checks happen in the routes (they need the HTTP context to audit refusals); the rules
here are the business rules that hold whoever is calling.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import defer
from sqlmodel import Session, col, func, select

from app.models import (
    AcceptanceRequest,
    ActionControl,
    AssessmentAction,
    Control,
    Evidence,
    Risk,
    RiskAssessment,
    TreatmentAction,
    TreatmentDecision,
    User,
)
from app.models.enums import (
    AcceptanceStatus,
    ActionStatus,
    AssessmentType,
    AuditAction,
    Band,
    EvidenceTarget,
    RiskStatus,
    Strategy,
)
from app.services import audit, governance
from app.services import register as reg
from app.services.clock import now_utc
from app.services.evidence import CheckedFile
from app.services.scoring import ScoreResult, remediation_due
from app.services.workflow import OPEN_ACTION_STATUSES, can_transition, check_transition

MAX_ACCEPTANCE_DAYS = 365
MIN_DECISION_COMMENT = 10


class TreatmentError(ValueError):
    """Business rule refused; `status` hints the HTTP code."""

    def __init__(self, message: str, status: int = 422) -> None:
        super().__init__(message)
        self.status = status


# ── Helpers ────────────────────────────────────────────────────────────────────────────────


def current_assessment(session: Session, risk_id: int) -> RiskAssessment | None:
    return session.exec(
        select(RiskAssessment)
        .where(RiskAssessment.risk_id == risk_id)
        .order_by(col(RiskAssessment.id).desc())
        .limit(1)
    ).first()


def latest_decision(session: Session, risk_id: int) -> TreatmentDecision | None:
    return session.exec(
        select(TreatmentDecision)
        .where(TreatmentDecision.risk_id == risk_id)
        .order_by(col(TreatmentDecision.id).desc())
        .limit(1)
    ).first()


def open_action_count(session: Session, risk_id: int, except_id: int | None = None) -> int:
    query = (
        select(func.count())
        .select_from(TreatmentAction)
        .where(
            TreatmentAction.risk_id == risk_id,
            col(TreatmentAction.status).in_(OPEN_ACTION_STATUSES),
        )
    )
    if except_id is not None:
        query = query.where(TreatmentAction.id != except_id)
    return session.exec(query).one()


def move_risk(
    session: Session, risk: Risk, target: RiskStatus, by: audit.AuditActor, why: str
) -> None:
    """Change a risk's status through the transition table, with an audit entry."""
    if risk.status == target.value:
        return
    check_transition("risk", risk.status, target.value)
    before = risk.status
    risk.status = target.value
    risk.updated_at = now_utc()
    session.add(risk)
    audit.record(
        session,
        AuditAction.UPDATE,
        by,
        object_type="risk",
        object_id=risk.id,
        before={"status": before},
        after={"status": target.value},
        detail=why,
    )


def _require_user(session: Session, user_id: int, label: str) -> User:
    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise TreatmentError(f"The {label} must be an active user.")
    return user


def _controls(session: Session, control_ids: list[int]) -> list[Control]:
    return reg.require_ids(session, Control, control_ids, "control")  # type: ignore[return-value]


# ── Decisions ──────────────────────────────────────────────────────────────────────────────


def decide_treatment(
    session: Session,
    by: audit.AuditActor,
    risk: Risk,
    *,
    strategy: Strategy,
    justification: str,
    target_likelihood: int | None = None,
    target_impact: int | None = None,
) -> TreatmentDecision:
    if risk.status == RiskStatus.CLOSED.value:
        raise TreatmentError("This risk is closed.", 409)
    if (target_likelihood is None) != (target_impact is None):
        raise TreatmentError("Give both target likelihood and target impact, or neither.")
    decision = TreatmentDecision(
        risk_id=risk.id,
        strategy=strategy.value,  # type: ignore[arg-type]
        justification=justification.strip(),
        target_likelihood=target_likelihood,
        target_impact=target_impact,
        decided_by_id=by.user_id,
    )  # type: ignore[arg-type]
    session.add(decision)
    session.flush()
    audit.record(
        session,
        AuditAction.CREATE,
        by,
        object_type="decision",
        object_id=decision.id,
        after={
            "risk_id": risk.id,
            "strategy": strategy.value,
            "target": [target_likelihood, target_impact],
        },
        detail=f"{risk.risk_code}: {strategy.value}",
    )
    return decision


# ── Actions ────────────────────────────────────────────────────────────────────────────────


def default_due_date(session: Session, risk: Risk) -> date:
    """The band's remediation SLA from today; Low risks (no SLA) get 90 days."""
    today = governance.org_today(session)
    current = current_assessment(session, risk.id)  # type: ignore[arg-type]
    if current is None:
        return today + timedelta(days=90)
    return remediation_due(Band(current.band), today, governance.policy(session)) or (
        today + timedelta(days=90)
    )


def create_action(
    session: Session,
    by: audit.AuditActor,
    risk: Risk,
    *,
    title: str,
    owner_id: int,
    description: str | None = None,
    due_date: date | None = None,
    estimated_cost_ngn: Decimal | None = None,
    control_ids: list[int] | None = None,
    action_code: str | None = None,
    **optional: Any,
) -> TreatmentAction:
    if risk.status == RiskStatus.CLOSED.value:
        raise TreatmentError("This risk is closed; reopen it before adding actions.", 409)
    _require_user(session, owner_id, "action owner")
    today = governance.org_today(session)
    due = due_date or default_due_date(session, risk)
    if due < today:
        raise TreatmentError("The due date can't be in the past.")
    controls = _controls(session, control_ids or [])
    if action_code is None:
        action_code = reg.next_code(session, TreatmentAction.action_code, "T-")
    elif session.exec(
        select(TreatmentAction.id).where(TreatmentAction.action_code == action_code)
    ).first():
        raise TreatmentError(f"Action code {action_code} is already used.", 409)

    action = TreatmentAction(
        action_code=action_code,
        risk_id=risk.id,
        title=title.strip(),  # type: ignore[arg-type]
        description=description,
        owner_id=owner_id,
        due_date=due,
        estimated_cost_ngn=estimated_cost_ngn,
        created_by_id=by.user_id,
        **optional,
    )  # type: ignore[arg-type]
    session.add(action)
    session.flush()
    for control in controls:
        session.add(ActionControl(action_id=action.id, control_id=control.id))  # type: ignore[arg-type]
    audit.record(
        session,
        AuditAction.CREATE,
        by,
        object_type="action",
        object_id=action.id,
        after={
            "action_code": action.action_code,
            "risk_id": risk.id,
            "title": action.title,
            "owner_id": owner_id,
            "due_date": due,
            "cost": estimated_cost_ngn,
            "control_ids": [c.id for c in controls],
        },
    )
    if risk.status in (
        RiskStatus.OPEN.value,
        RiskStatus.AWAITING_REASSESSMENT.value,
        RiskStatus.ACCEPTED.value,
    ):
        move_risk(
            session,
            risk,
            RiskStatus.TREATMENT_IN_PROGRESS,
            by,
            f"Treatment action {action.action_code} created",
        )
    return action


ACTION_FIELDS = ("title", "description", "owner_id", "due_date", "status", "estimated_cost_ngn")


def update_action(
    session: Session, by: audit.AuditActor, action: TreatmentAction, changes: dict[str, Any]
) -> TreatmentAction:
    """Progress and planning changes. Completion has its own function (it needs evidence)."""
    if action.status in (ActionStatus.COMPLETED.value, ActionStatus.CANCELLED.value):
        raise TreatmentError(f"This action is {action.status} and can't be changed.", 409)
    if changes.get("status") == ActionStatus.COMPLETED.value:
        raise TreatmentError("Use 'complete' to finish an action: it requires evidence.", 422)
    if "owner_id" in changes:
        _require_user(session, changes["owner_id"], "action owner")
    if "due_date" in changes and changes["due_date"] < governance.org_today(session):
        raise TreatmentError("The due date can't be in the past.")
    if "status" in changes:
        check_transition("action", action.status, changes["status"])
    before = {f: getattr(action, f) for f in ACTION_FIELDS}
    for field, value in changes.items():
        setattr(action, field, value)
    action.updated_at = now_utc()
    session.add(action)
    after = {f: getattr(action, f) for f in ACTION_FIELDS}
    audit.record(
        session,
        AuditAction.UPDATE,
        by,
        object_type="action",
        object_id=action.id,
        before={k: v for k, v in before.items() if v != after[k]},
        after={k: v for k, v in after.items() if v != before[k]},
    )
    if action.status == ActionStatus.CANCELLED.value:
        risk = session.get(Risk, action.risk_id)
        if (
            risk
            and risk.status == RiskStatus.TREATMENT_IN_PROGRESS.value
            and open_action_count(session, risk.id, except_id=action.id) == 0
        ):  # type: ignore[arg-type]
            move_risk(
                session,
                risk,
                RiskStatus.OPEN,
                by,
                f"Last open action {action.action_code} cancelled",
            )
    return action


def complete_action(
    session: Session,
    by: audit.AuditActor,
    action: TreatmentAction,
    *,
    note: str,
    evidence: CheckedFile,
    content: bytes,
) -> tuple[TreatmentAction, Evidence]:
    """Brief feature 4: completion is recorded with evidence and **never changes the score**;
    the risk waits for a documented reassessment."""
    check_transition("action", action.status, ActionStatus.COMPLETED.value)
    if not note or len(note.strip()) < 10:
        raise TreatmentError("Describe what was done (at least 10 characters).")
    stored = store_evidence(
        session,
        by,
        EvidenceTarget.ACTION,
        action.id,
        evidence,
        content,  # type: ignore[arg-type]
        description=f"Completion evidence for {action.action_code}",
    )
    action.status = ActionStatus.COMPLETED.value
    action.completed_at = now_utc()
    action.completed_by_id = by.user_id
    action.completion_note = note.strip()
    action.updated_at = action.completed_at
    session.add(action)
    session.flush()
    audit.record(
        session,
        AuditAction.COMPLETE,
        by,
        object_type="action",
        object_id=action.id,
        after={"status": "completed", "evidence_id": stored.id, "sha256": stored.sha256},
        detail=note.strip()[:200],
    )
    risk = session.get(Risk, action.risk_id)
    if risk and can_transition("risk", risk.status, RiskStatus.AWAITING_REASSESSMENT.value):
        move_risk(
            session,
            risk,
            RiskStatus.AWAITING_REASSESSMENT,
            by,
            f"Action {action.action_code} completed; score unchanged until reassessed",
        )
    return action, stored


def link_controls(session: Session, action: TreatmentAction, control_ids: list[int]) -> list[int]:
    controls = _controls(session, control_ids)
    for link in session.exec(select(ActionControl).where(ActionControl.action_id == action.id)):
        session.delete(link)
    session.flush()
    for control in controls:
        session.add(ActionControl(action_id=action.id, control_id=control.id))  # type: ignore[arg-type]
    return [c.id for c in controls]  # type: ignore[misc]


# ── Evidence ───────────────────────────────────────────────────────────────────────────────


def store_evidence(
    session: Session,
    by: audit.AuditActor,
    target_type: EvidenceTarget,
    target_id: int,
    checked: CheckedFile,
    content: bytes,
    *,
    description: str | None = None,
    supersedes_id: int | None = None,
) -> Evidence:
    if supersedes_id is not None:
        old = session.exec(
            select(Evidence)
            .options(defer(Evidence.content))  # type: ignore[arg-type]
            .where(Evidence.id == supersedes_id)
        ).first()
        if old is None or (old.target_type, old.target_id) != (target_type.value, target_id):
            raise TreatmentError("A file can only supersede evidence on the same record.")
    row = Evidence(
        target_type=target_type.value,
        target_id=target_id,
        original_name=checked.original_name,
        mime_type=checked.mime_type,
        size_bytes=checked.size_bytes,
        sha256=checked.sha256,
        content=content,
        description=description,
        supersedes_id=supersedes_id,
        uploaded_by_id=by.user_id,
    )  # type: ignore[arg-type]
    session.add(row)
    session.flush()
    audit.record(
        session,
        AuditAction.UPLOAD,
        by,
        object_type="evidence",
        object_id=row.id,
        after={
            "target": f"{target_type.value}:{target_id}",
            "name": row.original_name,
            "size": row.size_bytes,
            "sha256": row.sha256,
            "supersedes_id": supersedes_id,
        },
    )
    return row


def evidence_for(session: Session, target_type: str, target_id: int) -> list[Evidence]:
    return list(
        session.exec(
            select(Evidence)
            .options(defer(Evidence.content))  # type: ignore[arg-type]
            .where(Evidence.target_type == target_type, Evidence.target_id == target_id)
            .order_by(col(Evidence.id))
        )
    )


# ── Reassessment ───────────────────────────────────────────────────────────────────────────


def actions_awaiting_reassessment(session: Session, risk_id: int) -> list[TreatmentAction]:
    """Completed actions of the risk that no reassessment has followed yet, oldest first."""
    linked = select(AssessmentAction.action_id)
    return list(
        session.exec(
            select(TreatmentAction)
            .where(
                TreatmentAction.risk_id == risk_id,
                TreatmentAction.status == ActionStatus.COMPLETED.value,
                col(TreatmentAction.id).not_in(linked),
            )
            .order_by(col(TreatmentAction.completed_at), col(TreatmentAction.id))
        )
    )


def reassess(
    session: Session,
    by: audit.AuditActor,
    risk: Risk,
    *,
    likelihood: int,
    impact: int,
    rationale: str,
    evidence: CheckedFile,
    content: bytes,
    close_risk: bool = False,
) -> tuple[RiskAssessment, ScoreResult, Evidence]:
    """Brief feature 4: a documented reassessment, supported by evidence, as a new row. The
    original assessment is kept."""
    if risk.status == RiskStatus.CLOSED.value:
        raise TreatmentError("This risk is closed.", 409)
    if close_risk:
        decision = latest_decision(session, risk.id)  # type: ignore[arg-type]
        if decision is None or decision.strategy != Strategy.AVOID.value:
            raise TreatmentError(
                "Only a risk whose treatment strategy is 'avoid' can be closed by a reassessment.",
                409,
            )
        if open_action_count(session, risk.id) > 0:  # type: ignore[arg-type]
            raise TreatmentError(
                "Complete or cancel the open actions before closing the risk.", 409
            )
    try:
        row, result = reg.record_assessment(
            session,
            by,
            risk,
            likelihood=likelihood,
            impact=impact,
            rationale=rationale,
            assessment_type=AssessmentType.REASSESSMENT,
        )
    except reg.RegisterError as exc:
        raise TreatmentError(str(exc), exc.status) from exc
    # Record which completed actions this residual reassessment followed (insert-only links).
    followed = actions_awaiting_reassessment(session, risk.id)  # type: ignore[arg-type]
    for action in followed:
        session.add(AssessmentAction(assessment_id=row.id, action_id=action.id))  # type: ignore[arg-type]
    session.flush()
    stored = store_evidence(
        session,
        by,
        EvidenceTarget.ASSESSMENT,
        row.id,
        evidence,
        content,  # type: ignore[arg-type]
        description=f"Reassessment evidence for {risk.risk_code}",
    )
    if close_risk:
        move_risk(
            session, risk, RiskStatus.CLOSED, by, "Risk removed (avoid), confirmed by reassessment"
        )
    elif risk.status != RiskStatus.ACCEPTED.value:
        target = (
            RiskStatus.TREATMENT_IN_PROGRESS
            if open_action_count(session, risk.id)
            # type: ignore[arg-type]
            else RiskStatus.OPEN
        )
        move_risk(session, risk, target, by, f"Reassessed: {result.explanation}")
    return row, result, stored


# ── Acceptance ─────────────────────────────────────────────────────────────────────────────


def _check_expiry(session: Session, expiry: date, label: str) -> None:
    today = governance.org_today(session)
    if expiry <= today:
        raise TreatmentError(f"The {label} must be after today.")
    if expiry > today + timedelta(days=MAX_ACCEPTANCE_DAYS):
        raise TreatmentError(f"The {label} can be at most {MAX_ACCEPTANCE_DAYS} days ahead.")


def request_acceptance(
    session: Session, by: audit.AuditActor, risk: Risk, *, justification: str, proposed_expiry: date
) -> AcceptanceRequest:
    if risk.status == RiskStatus.CLOSED.value:
        raise TreatmentError("This risk is closed.", 409)
    if current_assessment(session, risk.id) is None:  # type: ignore[arg-type]
        raise TreatmentError("Assess the risk before asking to accept it.", 409)
    pending = session.exec(
        select(AcceptanceRequest.id).where(
            AcceptanceRequest.risk_id == risk.id,
            AcceptanceRequest.status == AcceptanceStatus.PENDING.value,
        )
    ).first()
    if pending is not None:
        raise TreatmentError("This risk already has a pending acceptance request.", 409)
    if len(justification.strip()) < 30:
        raise TreatmentError("The justification needs at least 30 characters.")
    _check_expiry(session, proposed_expiry, "proposed expiry date")
    request = AcceptanceRequest(
        risk_id=risk.id,
        requested_by_id=by.user_id,  # type: ignore[arg-type]
        justification=justification.strip(),
        proposed_expiry=proposed_expiry,
    )
    session.add(request)
    session.flush()
    audit.record(
        session,
        AuditAction.REQUEST,
        by,
        object_type="acceptance",
        object_id=request.id,
        after={"risk_id": risk.id, "proposed_expiry": proposed_expiry},
        detail=f"{risk.risk_code}: acceptance requested",
    )
    return request


def decide_acceptance(
    session: Session,
    by: audit.AuditActor,
    request: AcceptanceRequest,
    *,
    approve: bool,
    comment: str,
    expiry_date: date | None = None,
) -> AcceptanceRequest:
    """Separation of duties is checked by the caller (permissions.authorize); the database
    independently refuses a decider who is the requester."""
    if request.status != AcceptanceStatus.PENDING.value:
        raise TreatmentError(f"This request is already {request.status}.", 409)
    if not comment or len(comment.strip()) < MIN_DECISION_COMMENT:
        raise TreatmentError(f"Explain the decision (at least {MIN_DECISION_COMMENT} characters).")
    risk = session.get(Risk, request.risk_id)
    if risk is None or risk.status == RiskStatus.CLOSED.value:
        raise TreatmentError("The risk is closed or missing.", 409)
    new_status = AcceptanceStatus.APPROVED if approve else AcceptanceStatus.REJECTED
    check_transition("acceptance", request.status, new_status.value)
    if approve:
        expiry_date = expiry_date or request.proposed_expiry
        _check_expiry(session, expiry_date, "expiry date")
    request.status = new_status.value
    request.decided_by_id = by.user_id
    request.decision_date = now_utc()
    request.decision_comment = comment.strip()
    request.expiry_date = expiry_date if approve else None
    session.add(request)
    session.flush()
    audit.record(
        session,
        AuditAction.APPROVE if approve else AuditAction.REJECT,
        by,
        object_type="acceptance",
        object_id=request.id,
        after={"status": request.status, "expiry_date": request.expiry_date, "risk_id": risk.id},
        detail=f"{risk.risk_code}: {comment.strip()[:200]}",
    )
    if approve:
        move_risk(
            session,
            risk,
            RiskStatus.ACCEPTED,
            by,
            f"Acceptance {request.id} approved until {expiry_date}",
        )
    return request


def latest_approved_acceptance(session: Session, risk_id: int) -> AcceptanceRequest | None:
    return session.exec(
        select(AcceptanceRequest)
        .where(
            AcceptanceRequest.risk_id == risk_id,
            AcceptanceRequest.status == AcceptanceStatus.APPROVED.value,
        )
        .order_by(col(AcceptanceRequest.id).desc())
        .limit(1)
    ).first()
