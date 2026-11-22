"""Bodies for decisions, actions, evidence, reassessment and acceptance."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, StrictInt

from app.models.enums import AcceptanceStatus, ActionStatus, Strategy
from app.schemas.register import PersonRef, ScoreSummary


class DecisionCreate(BaseModel):
    strategy: Strategy
    justification: str = Field(min_length=10, max_length=5000)
    target_likelihood: StrictInt | None = Field(
        default=None, ge=1, le=5, description="Planned residual (a target only)"
    )
    target_impact: StrictInt | None = Field(default=None, ge=1, le=5)


class DecisionOut(BaseModel):
    id: int
    strategy: Strategy
    justification: str
    target_likelihood: int | None
    target_impact: int | None
    target_score: int | None
    decided_by: PersonRef
    decided_at: datetime


class ControlRef(BaseModel):
    id: int
    framework: str
    control_ref: str
    short_title: str


class ActionCreate(BaseModel):
    title: str = Field(min_length=5, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    owner_id: int
    due_date: date | None = Field(default=None, description="Defaults to the band's SLA")
    estimated_cost_ngn: Decimal | None = Field(default=None, ge=0, max_digits=16, decimal_places=2)
    control_ids: list[int] = Field(default_factory=list)


class ActionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=5, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    owner_id: int | None = None
    due_date: date | None = None
    status: Literal["in_progress", "cancelled"] | None = Field(
        default=None, description="Completion uses POST /actions/{id}/complete (with evidence)"
    )
    estimated_cost_ngn: Decimal | None = Field(default=None, ge=0, max_digits=16, decimal_places=2)
    control_ids: list[int] | None = None


class ActionOut(BaseModel):
    id: int
    action_code: str
    risk: dict[str, object]
    title: str
    description: str | None
    owner: PersonRef
    due_date: date
    status: ActionStatus
    overdue: bool
    days_overdue: int
    estimated_cost_ngn: Decimal | None
    controls: list[ControlRef]
    completed_at: datetime | None
    completed_by: PersonRef | None
    completion_note: str | None
    evidence_count: int
    can_update: bool
    created_at: datetime


class EvidenceOut(BaseModel):
    id: int
    target_type: str
    target_id: int
    original_name: str
    mime_type: str
    size_bytes: int
    sha256: str
    description: str | None
    supersedes_id: int | None
    superseded_by_id: int | None
    uploaded_by: PersonRef
    uploaded_at: datetime
    download_url: str


class AcceptanceCreate(BaseModel):
    justification: str = Field(min_length=30, max_length=5000)
    proposed_expiry: date


class AcceptanceDecision(BaseModel):
    decision: Literal["approve", "reject"]
    comment: str = Field(min_length=10, max_length=5000)
    expiry_date: date | None = Field(
        default=None, description="Approve only; defaults to the proposed expiry"
    )


class AcceptanceOut(BaseModel):
    id: int
    risk: dict[str, object]
    current: ScoreSummary | None
    requested_by: PersonRef
    requested_at: datetime
    justification: str
    proposed_expiry: date
    status: AcceptanceStatus
    expired: bool
    decided_by: PersonRef | None
    decision_date: datetime | None
    decision_comment: str | None
    expiry_date: date | None
    can_decide: bool
    cannot_decide_reason: str | None


class ReassessmentOut(BaseModel):
    assessment_id: int
    score: int
    band: str
    above_appetite: bool
    explanation: str
    original_score: int | None
    risk_status: str
    evidence: EvidenceOut
