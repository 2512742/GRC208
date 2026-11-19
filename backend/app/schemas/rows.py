"""CSV row formats for assets and risks: the import templates (brief feature 8).

`seed-demo` loads `app/sample_data/alajo_*.csv` through exactly these models, and the CSV import
(P6) will too, so a WS2 edit that passes the seed also passes the import, and vice versa.
List cells use semicolons: `A-003;A-001`.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator

from app.models.enums import AssetType, Classification, Strategy


def split_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [part.strip() for part in str(value).split(";") if part.strip()]


def blank_to_none(value: object) -> object:
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


class _Row(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class AssetRow(_Row):
    asset_code: str | None = Field(default=None, pattern=r"^A-\d{3,4}$")
    name: str = Field(min_length=2, max_length=120)
    asset_type: AssetType
    service_code: str = Field(pattern=r"^S\d{1,3}$")
    owner_username: str | None = None
    classification: Classification = Classification.CONFIDENTIAL
    obligations: list[str] = Field(default_factory=list, description="e.g. NDPA-02;PCI-03")
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("asset_code", "owner_username", "description", mode="before")
    @classmethod
    def _blank(cls, value: object) -> object:
        return blank_to_none(value)

    @field_validator("obligations", mode="before")
    @classmethod
    def _lists(cls, value: object) -> list[str]:
        return split_list(value)

    @field_validator("asset_type", "classification", mode="before")
    @classmethod
    def _lower(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value


class RiskRow(_Row):
    risk_code: str | None = Field(default=None, pattern=r"^R-\d{3,4}$")
    title: str = Field(min_length=5, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    asset_codes: list[str] = Field(min_length=1, description="At least one, e.g. A-003;A-001")
    owner_username: str
    likelihood: StrictInt | None = Field(default=None, ge=1, le=5)
    impact: StrictInt | None = Field(default=None, ge=1, le=5)
    category: str | None = Field(default=None, max_length=60)
    obligations: list[str] = Field(default_factory=list)
    threat: str = Field(min_length=1, max_length=5000)
    vulnerability: str = Field(min_length=1, max_length=5000)
    business_impact: str = Field(min_length=1, max_length=5000)
    rationale: str | None = Field(default=None, max_length=5000)

    @field_validator("risk_code", "description", "category", "rationale", mode="before")
    @classmethod
    def _blank(cls, value: object) -> object:
        return blank_to_none(value)

    @field_validator("asset_codes", "obligations", mode="before")
    @classmethod
    def _lists(cls, value: object) -> list[str]:
        return split_list(value)

    @field_validator("likelihood", "impact", mode="before")
    @classmethod
    def _ints(cls, value: object) -> object:
        """CSV cells are text: '4' becomes 4; '4.5', 'high' or '' stay invalid or empty."""
        if isinstance(value, str) and value.strip().isdigit():
            return int(value)
        return blank_to_none(value)

    @model_validator(mode="after")
    def _score_complete(self) -> Self:
        scored = (self.likelihood is not None, self.impact is not None)
        if any(scored) and not all(scored):
            raise ValueError("give both likelihood and impact, or neither")
        if all(scored) and not self.rationale:
            raise ValueError("a scored risk needs a rationale")
        return self


class DecisionRow(_Row):
    """sample_data/alajo_decisions.csv: the treatment strategy per risk."""

    risk_code: str = Field(pattern=r"^R-\d{3,4}$")
    strategy: Strategy
    justification: str = Field(min_length=10, max_length=5000)
    target_likelihood: StrictInt | None = Field(default=None, ge=1, le=5)
    target_impact: StrictInt | None = Field(default=None, ge=1, le=5)

    @field_validator("target_likelihood", "target_impact", mode="before")
    @classmethod
    def _ints(cls, value: object) -> object:
        if isinstance(value, str) and value.strip().isdigit():
            return int(value)
        return blank_to_none(value)

    @field_validator("strategy", mode="before")
    @classmethod
    def _lower(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value


class TreatmentRow(_Row):
    """sample_data/alajo_treatments.csv: treatment actions. `due_in_days` is relative to the
    day the seed runs (negative = already past), so overdue examples stay overdue on demo day."""

    action_code: str = Field(pattern=r"^T-\d{3,4}$")
    risk_code: str = Field(pattern=r"^R-\d{3,4}$")
    title: str = Field(min_length=5, max_length=200)
    owner_username: str
    due_in_days: int = Field(ge=-40, le=365)
    status: Literal["not_started", "in_progress", "completed"]
    estimated_cost_ngn: Decimal | None = Field(default=None, ge=0)
    controls: list[str] = Field(default_factory=list, description="e.g. PR.DS;A.8.24")
    completion_note: str | None = None

    @field_validator("controls", mode="before")
    @classmethod
    def _lists(cls, value: object) -> list[str]:
        return split_list(value)

    @field_validator("estimated_cost_ngn", "completion_note", mode="before")
    @classmethod
    def _blank(cls, value: object) -> object:
        return blank_to_none(value)

    @model_validator(mode="after")
    def _completion(self) -> Self:
        if self.status == "completed" and not self.completion_note:
            raise ValueError("a completed action needs a completion_note")
        return self
