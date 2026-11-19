"""Business services, assets, obligations, controls, risks and assessments.

Covers brief features 1 (register), 2 (scoring) and 4 (residual assessment history).
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import CheckConstraint, Index, UniqueConstraint, text
from sqlmodel import Field, SQLModel

from app.models.base import UTCDateTime, allowed, between
from app.models.enums import (
    AssessmentType,
    AssetStatus,
    AssetType,
    Band,
    Classification,
    Framework,
    Regime,
    RiskStatus,
)
from app.services.clock import now_utc

# Band boundaries from the methodology (PLAN.md §2.4), enforced by the database too.
BAND_RULE = (
    "(score BETWEEN 1 AND 4 AND band = 'low') OR "
    "(score BETWEEN 5 AND 9 AND band = 'medium') OR "
    "(score BETWEEN 10 AND 14 AND band = 'high') OR "
    "(score BETWEEN 15 AND 25 AND band = 'critical')"
)


class BusinessService(SQLModel, table=True):
    __tablename__ = "business_service"
    __table_args__ = (between("criticality", 1, 5),)

    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(max_length=10, unique=True)  # S1, S2, S3
    name: str = Field(max_length=120, unique=True)
    description: str | None = None
    owner_id: int | None = Field(default=None, foreign_key="user_account.id", ondelete="RESTRICT")
    criticality: int = Field(default=3)


class Asset(SQLModel, table=True):
    __tablename__ = "asset"
    __table_args__ = (
        UniqueConstraint("name", "service_id", name="uq_asset_name_service"),  # natural key
        allowed("asset_type", AssetType),
        allowed("classification", Classification),
        allowed("status", AssetStatus),
        CheckConstraint("asset_code LIKE 'A-%'", name="asset_code_format"),
    )

    id: int | None = Field(default=None, primary_key=True)
    asset_code: str = Field(max_length=10, unique=True)  # A-001
    name: str = Field(max_length=120)
    asset_type: str = Field(max_length=30)
    service_id: int = Field(foreign_key="business_service.id", ondelete="RESTRICT", index=True)
    owner_id: int | None = Field(default=None, foreign_key="user_account.id", ondelete="RESTRICT")
    classification: str = Field(default=Classification.CONFIDENTIAL.value, max_length=20)
    status: str = Field(default=AssetStatus.ACTIVE.value, max_length=20)
    description: str | None = None
    created_at: datetime = Field(default_factory=now_utc, sa_type=UTCDateTime, nullable=False)


class Obligation(SQLModel, table=True):
    """A regulatory obligation (NDPA, CBN, SEC Nigeria, PCI DSS). Descriptive only."""

    __tablename__ = "obligation"
    __table_args__ = (
        UniqueConstraint("regime", "reference", name="uq_obligation_regime_reference"),
        allowed("regime", Regime),
    )

    id: int | None = Field(default=None, primary_key=True)
    regime: str = Field(max_length=20)
    reference: str = Field(max_length=40)
    short_title: str = Field(max_length=200)
    source_note: str | None = Field(default=None, max_length=300)


class Control(SQLModel, table=True):
    """Framework control reference: IDs plus our own short titles (ISO text is copyrighted)."""

    __tablename__ = "control"
    __table_args__ = (
        UniqueConstraint("framework", "control_ref", name="uq_control_framework_ref"),
        allowed("framework", Framework),
    )

    id: int | None = Field(default=None, primary_key=True)
    framework: str = Field(max_length=20)
    control_ref: str = Field(max_length=20)
    short_title: str = Field(max_length=200)


class AssetObligation(SQLModel, table=True):
    __tablename__ = "asset_obligation"

    asset_id: int = Field(foreign_key="asset.id", ondelete="CASCADE", primary_key=True)
    obligation_id: int = Field(foreign_key="obligation.id", ondelete="RESTRICT", primary_key=True)


class Risk(SQLModel, table=True):
    __tablename__ = "risk"
    __table_args__ = (
        allowed("status", RiskStatus),
        CheckConstraint("risk_code LIKE 'R-%'", name="risk_code_format"),
        CheckConstraint("length(title) >= 5", name="title_length"),
    )

    id: int | None = Field(default=None, primary_key=True)
    risk_code: str = Field(max_length=10, unique=True)  # R-001
    title: str = Field(max_length=200)
    description: str
    threat: str
    vulnerability: str
    business_impact: str
    category: str | None = Field(default=None, max_length=60)
    owner_id: int = Field(foreign_key="user_account.id", ondelete="RESTRICT", index=True)
    status: str = Field(default=RiskStatus.OPEN.value, max_length=30)
    next_review_date: date | None = None
    created_by_id: int = Field(foreign_key="user_account.id", ondelete="RESTRICT")
    created_at: datetime = Field(default_factory=now_utc, sa_type=UTCDateTime, nullable=False)
    updated_at: datetime = Field(default_factory=now_utc, sa_type=UTCDateTime, nullable=False)


class RiskAsset(SQLModel, table=True):
    """Each risk links to one or more assets (the 'at least one' rule is enforced by the API)."""

    __tablename__ = "risk_asset"

    risk_id: int = Field(foreign_key="risk.id", ondelete="CASCADE", primary_key=True)
    asset_id: int = Field(foreign_key="asset.id", ondelete="RESTRICT", primary_key=True)


class RiskObligation(SQLModel, table=True):
    __tablename__ = "risk_obligation"

    risk_id: int = Field(foreign_key="risk.id", ondelete="CASCADE", primary_key=True)
    obligation_id: int = Field(foreign_key="obligation.id", ondelete="RESTRICT", primary_key=True)


class RiskAssessment(SQLModel, table=True):
    """One scoring of a risk. Insert-only: a database trigger blocks UPDATE and DELETE.

    The current score of a risk is its latest row; the original is its single 'initial' row.
    Score, band and appetite flag are stored and cross-checked by the database, with the
    threshold in force at the time kept as a snapshot.
    """

    __tablename__ = "risk_assessment"
    __table_args__ = (
        allowed("assessment_type", AssessmentType),
        allowed("band", Band),
        between("likelihood", 1, 5),
        between("impact", 1, 5),
        between("appetite_threshold", 1, 25),
        CheckConstraint("score = likelihood * impact", name="score_is_l_times_i"),
        CheckConstraint(BAND_RULE, name="band_matches_score"),
        CheckConstraint(
            "above_appetite = (score >= appetite_threshold)", name="appetite_flag_matches"
        ),
        CheckConstraint("length(trim(rationale)) > 0", name="rationale_required"),
        Index(
            "uq_risk_assessment_one_initial",
            "risk_id",
            unique=True,
            sqlite_where=text("assessment_type = 'initial'"),
            postgresql_where=text("assessment_type = 'initial'"),
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    risk_id: int = Field(foreign_key="risk.id", ondelete="RESTRICT", index=True)
    assessment_type: str = Field(max_length=20)
    likelihood: int
    impact: int
    score: int
    band: str = Field(max_length=10)
    above_appetite: bool
    appetite_threshold: int
    rationale: str
    assessed_by_id: int = Field(foreign_key="user_account.id", ondelete="RESTRICT")
    assessed_at: datetime = Field(default_factory=now_utc, sa_type=UTCDateTime, nullable=False)
