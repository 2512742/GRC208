"""Bodies for imports, the audit log and governance settings."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.core.timezones import DISPLAY_TIMEZONES, SYSTEM


class ImportRowResult(BaseModel):
    row: int
    status: str  # valid | rejected | duplicate
    reasons: list[str]
    values: dict[str, Any]
    created: str | None = None


class ImportBatchOut(BaseModel):
    id: int
    import_type: str
    status: str
    uploaded_by: str
    uploaded_at: datetime
    committed_at: datetime | None
    file_name: str | None
    evidence_id: int | None
    total_rows: int
    valid_rows: int
    rejected_rows: int
    duplicate_rows: int
    rows: list[ImportRowResult]


class AuditEntryOut(BaseModel):
    id: int
    occurred_at: datetime
    username: str | None
    role: str | None
    action: str
    object_type: str | None
    object_id: str | None
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    detail: str | None
    ip: str | None
    hash: str


class AuditPage(BaseModel):
    items: list[AuditEntryOut]
    total: int
    page: int
    page_size: int


class ChainReportOut(BaseModel):
    ok: bool
    entries_checked: int
    first_broken_id: int | None
    problem: str | None
    head_hash: str | None = Field(
        description="Hash of the newest entry: note it down to detect later truncation of the log"
    )


class SettingsOut(BaseModel):
    appetite_threshold: int
    review_warning_days: int
    sla_days_critical: int
    sla_days_high: int
    sla_days_medium: int
    review_days_critical: int
    review_days_high: int
    review_days_medium: int
    review_days_low: int
    org_timezone: str
    updated_at: datetime
    updated_by: str | None


class SettingsUpdate(BaseModel):
    appetite_threshold: int | None = Field(default=None, ge=1, le=25)
    review_warning_days: int | None = Field(default=None, ge=1, le=365)
    sla_days_critical: int | None = Field(default=None, ge=1, le=365)
    sla_days_high: int | None = Field(default=None, ge=1, le=365)
    sla_days_medium: int | None = Field(default=None, ge=1, le=730)
    review_days_critical: int | None = Field(default=None, ge=1, le=365)
    review_days_high: int | None = Field(default=None, ge=1, le=365)
    review_days_medium: int | None = Field(default=None, ge=1, le=730)
    review_days_low: int | None = Field(default=None, ge=1, le=730)
    org_timezone: str | None = None

    @field_validator("org_timezone")
    @classmethod
    def _zone(cls, value: str | None) -> str | None:
        if value is not None and (value == SYSTEM or value not in DISPLAY_TIMEZONES):
            raise ValueError("must be one of the listed time zones (not 'system')")
        return value
