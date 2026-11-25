"""Treatment decisions, actions and risk acceptance (brief features 3 and 5)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint
from sqlmodel import Field, SQLModel

from app.models.base import UTCDateTime, allowed
from app.models.enums import AcceptanceStatus, ActionStatus, Strategy
from app.services.clock import now_utc

MIN_ACCEPTANCE_JUSTIFICATION = 30  # characters (adopted from the group's design)


class TreatmentDecision(SQLModel, table=True):
    """The chosen strategy for a risk. Insert-only: a new decision supersedes the previous one.

    target_likelihood/target_impact are the *planned* residual, labelled as a target and never
    used as the current score.
    """

    __tablename__ = "treatment_decision"
    __table_args__ = (
        allowed("strategy", Strategy),
        CheckConstraint(
            "target_likelihood IS NULL OR target_likelihood BETWEEN 1 AND 5",
            name="target_likelihood_range",
        ),
        CheckConstraint(
            "target_impact IS NULL OR target_impact BETWEEN 1 AND 5", name="target_impact_range"
        ),
        CheckConstraint("length(trim(justification)) > 0", name="justification_required"),
    )

    id: int | None = Field(default=None, primary_key=True)
    risk_id: int = Field(foreign_key="risk.id", ondelete="RESTRICT", index=True)
    strategy: str = Field(max_length=10)
    justification: str
    target_likelihood: int | None = None
    target_impact: int | None = None
    decided_by_id: int = Field(foreign_key="user_account.id", ondelete="RESTRICT")
    decided_at: datetime = Field(default_factory=now_utc, sa_type=UTCDateTime, nullable=False)


class TreatmentAction(SQLModel, table=True):
    __tablename__ = "treatment_action"
    __table_args__ = (
        allowed("status", ActionStatus),
        CheckConstraint("action_code LIKE 'T-%'", name="action_code_format"),
        CheckConstraint(
            "estimated_cost_ngn IS NULL OR estimated_cost_ngn >= 0", name="cost_not_negative"
        ),
        CheckConstraint(
            "status <> 'completed' OR (completed_at IS NOT NULL AND completed_by_id IS NOT NULL"
            " AND completion_note IS NOT NULL)",
            name="completion_recorded",
        ),
        CheckConstraint("aro IS NULL OR aro >= 0", name="aro_not_negative"),
        CheckConstraint(
            "effectiveness IS NULL OR (effectiveness >= 0 AND effectiveness <= 1)",
            name="effectiveness_fraction",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    action_code: str = Field(max_length=10, unique=True)  # T-001
    risk_id: int = Field(foreign_key="risk.id", ondelete="RESTRICT", index=True)
    title: str = Field(max_length=200)
    description: str | None = None
    owner_id: int = Field(foreign_key="user_account.id", ondelete="RESTRICT", index=True)
    due_date: date
    status: str = Field(default=ActionStatus.NOT_STARTED.value, max_length=20)
    estimated_cost_ngn: Decimal | None = Field(default=None, max_digits=16, decimal_places=2)
    completed_at: datetime | None = Field(default=None, sa_type=UTCDateTime)
    completed_by_id: int | None = Field(
        default=None, foreign_key="user_account.id", ondelete="RESTRICT"
    )
    completion_note: str | None = None
    # Optional cost-benefit inputs (GRC103 Lab 3 model): ALE = SLE x ARO.
    sle_ngn: Decimal | None = Field(default=None, max_digits=16, decimal_places=2)
    aro: Decimal | None = Field(default=None, max_digits=8, decimal_places=3)
    effectiveness: Decimal | None = Field(default=None, max_digits=4, decimal_places=3)
    created_by_id: int = Field(foreign_key="user_account.id", ondelete="RESTRICT")
    created_at: datetime = Field(default_factory=now_utc, sa_type=UTCDateTime, nullable=False)
    updated_at: datetime = Field(default_factory=now_utc, sa_type=UTCDateTime, nullable=False)


class ActionControl(SQLModel, table=True):
    __tablename__ = "action_control"

    action_id: int = Field(foreign_key="treatment_action.id", ondelete="CASCADE", primary_key=True)
    control_id: int = Field(foreign_key="control.id", ondelete="RESTRICT", primary_key=True)


class AssessmentAction(SQLModel, table=True):
    """Which completed treatment actions a residual reassessment followed (brief feature 4).

    Filled once, when the reassessment is recorded, and never changed: it lets the history say
    "reassessed after T-001 was completed".
    """

    __tablename__ = "assessment_action"

    assessment_id: int = Field(
        foreign_key="risk_assessment.id", ondelete="RESTRICT", primary_key=True
    )
    action_id: int = Field(foreign_key="treatment_action.id", ondelete="RESTRICT", primary_key=True)


class AcceptanceRequest(SQLModel, table=True):
    """Request to accept a risk, decided by an approver.

    The database itself refuses: a decider who is also the requester, a short justification,
    and decisions missing their date or expiry. "Owner can't approve their own risk" and the
    CISO/CRO failover need the risk's owner, so the API enforces those (tested in P5).
    """

    __tablename__ = "acceptance_request"
    __table_args__ = (
        allowed("status", AcceptanceStatus),
        CheckConstraint(
            f"length(trim(justification)) >= {MIN_ACCEPTANCE_JUSTIFICATION}",
            name="justification_length",
        ),
        CheckConstraint(
            "decided_by_id IS NULL OR decided_by_id <> requested_by_id",
            name="requester_cannot_decide",
        ),
        CheckConstraint(
            "(status = 'pending' AND decided_by_id IS NULL AND decision_date IS NULL) OR "
            "(status <> 'pending' AND decided_by_id IS NOT NULL AND decision_date IS NOT NULL)",
            name="decision_recorded",
        ),
        CheckConstraint(
            "status <> 'approved' OR expiry_date IS NOT NULL", name="approval_has_expiry"
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    risk_id: int = Field(foreign_key="risk.id", ondelete="RESTRICT", index=True)
    requested_by_id: int = Field(foreign_key="user_account.id", ondelete="RESTRICT")
    requested_at: datetime = Field(default_factory=now_utc, sa_type=UTCDateTime, nullable=False)
    justification: str
    proposed_expiry: date
    status: str = Field(default=AcceptanceStatus.PENDING.value, max_length=10)
    decided_by_id: int | None = Field(
        default=None, foreign_key="user_account.id", ondelete="RESTRICT"
    )
    decision_date: datetime | None = Field(default=None, sa_type=UTCDateTime)
    decision_comment: str | None = None
    expiry_date: date | None = None
