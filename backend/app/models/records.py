"""Evidence, audit log, CSV import batches and application settings (brief features 3, 7, 8)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, CheckConstraint, Column, LargeBinary
from sqlmodel import Field, SQLModel

from app.models.base import UTCDateTime, allowed, between
from app.models.enums import AuditAction, EvidenceTarget, ImportStatus, ImportType
from app.services.clock import now_utc

EVIDENCE_MAX_BYTES = 4 * 1024 * 1024  # Vercel request bodies are capped at about 4.5 MB
GENESIS_HASH = "0" * 64  # prev_hash of the first audit entry


class Evidence(SQLModel, table=True):
    """An uploaded file attached to a record. Insert-only: never edited or deleted.

    A mistake is fixed by uploading a new file whose `supersedes_id` points at the old one.
    Bytes live in the database (hosted) or on disk (`storage_path`, container option).
    """

    __tablename__ = "evidence"
    __table_args__ = (
        allowed("target_type", EvidenceTarget),
        CheckConstraint(f"size_bytes BETWEEN 1 AND {EVIDENCE_MAX_BYTES}", name="size_limit"),
        CheckConstraint("length(sha256) = 64", name="sha256_length"),
        CheckConstraint(
            "content IS NOT NULL OR storage_path IS NOT NULL", name="has_content_or_path"
        ),
        CheckConstraint(
            "supersedes_id IS NULL OR supersedes_id <> id", name="not_self_superseding"
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    target_type: str = Field(max_length=20)
    target_id: int = Field(index=True)
    original_name: str = Field(max_length=255)
    mime_type: str = Field(max_length=100)
    size_bytes: int
    sha256: str = Field(max_length=64, index=True)
    content: bytes | None = Field(default=None, sa_column=Column(LargeBinary, nullable=True))
    storage_path: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=500)
    supersedes_id: int | None = Field(default=None, foreign_key="evidence.id", ondelete="RESTRICT")
    uploaded_by_id: int = Field(foreign_key="user_account.id", ondelete="RESTRICT")
    uploaded_at: datetime = Field(default_factory=now_utc, sa_type=UTCDateTime, nullable=False)


class AuditLog(SQLModel, table=True):
    """Append-only, hash-chained log. Each row stores the SHA-256 of the previous row.

    `prev_hash` is unique, so two writers can never both extend the chain from the same row:
    the chain cannot fork even under concurrent serverless instances.
    """

    __tablename__ = "audit_log"
    __table_args__ = (
        allowed("action", AuditAction),
        CheckConstraint("length(prev_hash) = 64 AND length(hash) = 64", name="hash_lengths"),
    )

    id: int | None = Field(default=None, primary_key=True)
    occurred_at: datetime = Field(default_factory=now_utc, sa_type=UTCDateTime, nullable=False)
    user_id: int | None = Field(default=None, foreign_key="user_account.id", ondelete="RESTRICT")
    username: str | None = Field(default=None, max_length=50)  # snapshot at the time
    role: str | None = Field(default=None, max_length=20)  # snapshot at the time
    action: str = Field(max_length=20, index=True)
    object_type: str | None = Field(default=None, max_length=40)
    object_id: str | None = Field(default=None, max_length=40)
    before: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    after: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    detail: str | None = Field(default=None, max_length=500)
    ip: str | None = Field(default=None, max_length=45)
    prev_hash: str = Field(max_length=64, unique=True)
    hash: str = Field(max_length=64, unique=True)


class ImportBatch(SQLModel, table=True):
    __tablename__ = "import_batch"
    __table_args__ = (
        allowed("import_type", ImportType),
        allowed("status", ImportStatus),
        CheckConstraint(
            "total_rows >= 0 AND valid_rows >= 0 AND rejected_rows >= 0 AND duplicate_rows >= 0",
            name="counts_not_negative",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    import_type: str = Field(max_length=10)
    evidence_id: int | None = Field(default=None, foreign_key="evidence.id", ondelete="RESTRICT")
    uploaded_by_id: int = Field(foreign_key="user_account.id", ondelete="RESTRICT")
    uploaded_at: datetime = Field(default_factory=now_utc, sa_type=UTCDateTime, nullable=False)
    status: str = Field(default=ImportStatus.PREVIEWED.value, max_length=10)
    total_rows: int = 0
    valid_rows: int = 0
    rejected_rows: int = 0
    duplicate_rows: int = 0
    row_results: list[dict[str, Any]] | None = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )
    committed_at: datetime | None = Field(default=None, sa_type=UTCDateTime)


class AppSetting(SQLModel, table=True):
    """Single row (id = 1) of tunable governance settings. Every change is audited."""

    __tablename__ = "app_setting"
    __table_args__ = (
        CheckConstraint("id = 1", name="single_row"),
        between("appetite_threshold", 1, 25),
        CheckConstraint(
            "review_warning_days > 0 AND sla_days_critical > 0 AND sla_days_high > 0 AND "
            "sla_days_medium > 0 AND review_days_critical > 0 AND review_days_high > 0 AND "
            "review_days_medium > 0 AND review_days_low > 0",
            name="positive_periods",
        ),
    )

    id: int = Field(default=1, primary_key=True)
    appetite_threshold: int = 10
    review_warning_days: int = 30
    # Remediation SLA: default due date for new actions, by band (Low has none).
    sla_days_critical: int = 30
    sla_days_high: int = 90
    sla_days_medium: int = 180
    # Review cycle: next_review_date after each assessment, by band.
    review_days_critical: int = 30
    review_days_high: int = 90
    review_days_medium: int = 180
    review_days_low: int = 365
    org_timezone: str = Field(default="Africa/Lagos", max_length=64)
    updated_at: datetime = Field(default_factory=now_utc, sa_type=UTCDateTime, nullable=False)
    updated_by_id: int | None = Field(
        default=None, foreign_key="user_account.id", ondelete="RESTRICT"
    )
