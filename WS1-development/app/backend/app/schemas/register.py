"""Request and response bodies for services, assets, obligations, controls, risks, assessments."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator

from app.models.enums import (
    AssetStatus,
    AssetType,
    Band,
    Classification,
    Framework,
    Regime,
    RiskStatus,
)

Scale = Annotated[StrictInt, Field(ge=1, le=5, description="1 (lowest) to 5 (highest)")]
Text = Annotated[str, Field(min_length=1, max_length=5000)]


def _strip(value: object) -> object:
    return value.strip() if isinstance(value, str) else value


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int


class PersonRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    full_name: str
    role: str
    job_title: str | None = None


# ── Services ───────────────────────────────────────────────────────────────────────────────


class ServiceCreate(BaseModel):
    code: str = Field(pattern=r"^S\d{1,3}$")
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    owner_id: int | None = None
    criticality: int = Field(default=3, ge=1, le=5)


class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    owner_id: int | None = None
    criticality: int | None = Field(default=None, ge=1, le=5)


class ServiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    description: str | None
    owner: PersonRef | None
    criticality: int
    asset_count: int
    risk_count: int


# ── Obligations and controls ───────────────────────────────────────────────────────────────


class ObligationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    regime: Regime
    reference: str
    short_title: str
    source_note: str | None


class ObligationCreate(BaseModel):
    regime: Regime
    reference: str = Field(min_length=2, max_length=40)
    short_title: str = Field(min_length=5, max_length=200)
    source_note: str | None = Field(default=None, max_length=300)


class ControlOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    framework: Framework
    control_ref: str
    short_title: str


# ── Assets ─────────────────────────────────────────────────────────────────────────────────


class AssetCreate(BaseModel):
    asset_code: str | None = Field(default=None, pattern=r"^A-\d{3,4}$")
    name: str = Field(min_length=2, max_length=120)
    asset_type: AssetType
    service_id: int
    owner_id: int | None = None
    classification: Classification = Classification.CONFIDENTIAL
    status: AssetStatus = AssetStatus.ACTIVE
    description: str | None = Field(default=None, max_length=2000)
    obligation_ids: list[int] = Field(default_factory=list)

    @field_validator("name", mode="before")
    @classmethod
    def _strip_name(cls, value: object) -> object:
        return _strip(value)


class AssetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    asset_type: AssetType | None = None
    owner_id: int | None = None
    classification: Classification | None = None
    status: AssetStatus | None = None
    description: str | None = Field(default=None, max_length=2000)
    obligation_ids: list[int] | None = None


class AssetRef(BaseModel):
    id: int
    asset_code: str
    name: str
    service_code: str


class AssetOut(BaseModel):
    id: int
    asset_code: str
    name: str
    asset_type: AssetType
    classification: Classification
    status: AssetStatus
    description: str | None
    service: dict[str, object]
    owner: PersonRef | None
    obligations: list[ObligationOut]
    risk_count: int
    highest_score: int | None


# ── Assessments ────────────────────────────────────────────────────────────────────────────


class AssessmentCreate(BaseModel):
    likelihood: Scale
    impact: Scale
    rationale: str = Field(
        min_length=10, max_length=5000, description="Why these values; cite the evidence relied on"
    )


class AssessmentOut(BaseModel):
    id: int
    assessment_type: str
    likelihood: int
    impact: int
    score: int
    band: Band
    above_appetite: bool
    appetite_threshold: int
    rationale: str
    explanation: str
    assessed_by: PersonRef
    assessed_at: datetime


class ScoreSummary(BaseModel):
    likelihood: int
    impact: int
    score: int
    band: Band
    above_appetite: bool
    explanation: str


# ── Risks ──────────────────────────────────────────────────────────────────────────────────


class RiskCreate(BaseModel):
    title: str = Field(min_length=5, max_length=200)
    description: Text
    threat: Text
    vulnerability: Text
    business_impact: Text
    category: str | None = Field(default=None, max_length=60)
    owner_id: int
    asset_ids: list[int] = Field(min_length=1, description="At least one linked asset")
    obligation_ids: list[int] = Field(default_factory=list)
    initial_assessment: AssessmentCreate | None = Field(
        default=None, description="Optional: score the risk in the same step"
    )


class RiskUpdate(BaseModel):
    """Analysts may change any field; a risk owner only `description` and `next_review_date`."""

    title: str | None = Field(default=None, min_length=5, max_length=200)
    description: str | None = Field(default=None, min_length=1, max_length=5000)
    threat: str | None = Field(default=None, min_length=1, max_length=5000)
    vulnerability: str | None = Field(default=None, min_length=1, max_length=5000)
    business_impact: str | None = Field(default=None, min_length=1, max_length=5000)
    category: str | None = Field(default=None, max_length=60)
    owner_id: int | None = None
    next_review_date: date | None = None
    asset_ids: list[int] | None = Field(default=None, min_length=1)
    obligation_ids: list[int] | None = None


OWNER_EDITABLE = frozenset({"description", "next_review_date"})


class RiskSummary(BaseModel):
    id: int
    risk_code: str
    title: str
    category: str | None
    status: RiskStatus
    owner: PersonRef
    assets: list[AssetRef]
    services: list[str]
    current: ScoreSummary | None
    original_score: int | None
    next_review_date: date | None
    review_due_soon: bool
    display_status: str = Field(description="status, or 'acceptance_expired' when it lapsed")
    strategy: str | None = Field(default=None, description="Latest treatment decision")
    open_actions: int = 0
    overdue_actions: int = 0
    acceptance_expiry: date | None = None


class RiskDetail(RiskSummary):
    description: str
    threat: str
    vulnerability: str
    business_impact: str
    obligations: list[ObligationOut]
    assessments: list[AssessmentOut]
    created_by: PersonRef
    created_at: datetime
    updated_at: datetime
