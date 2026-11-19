"""All tables. Importing this package registers every table on SQLModel.metadata.

Alembic relies on that registration to autogenerate migrations.
"""

from app.models.base import UTCDateTime  # noqa: F401  (also sets the naming convention)
from app.models.people import User, UserSession
from app.models.records import AppSetting, AuditLog, Evidence, ImportBatch
from app.models.register import (
    Asset,
    AssetObligation,
    BusinessService,
    Control,
    Obligation,
    Risk,
    RiskAssessment,
    RiskAsset,
    RiskObligation,
)
from app.models.treatment import (
    AcceptanceRequest,
    ActionControl,
    TreatmentAction,
    TreatmentDecision,
)

# Tables a database trigger protects from UPDATE and DELETE (see the baseline migration).
INSERT_ONLY_TABLES = ("risk_assessment", "treatment_decision", "evidence", "audit_log")

__all__ = [
    "INSERT_ONLY_TABLES",
    "AcceptanceRequest",
    "ActionControl",
    "AppSetting",
    "Asset",
    "AssetObligation",
    "AuditLog",
    "BusinessService",
    "Control",
    "Evidence",
    "ImportBatch",
    "Obligation",
    "Risk",
    "RiskAsset",
    "RiskAssessment",
    "RiskObligation",
    "TreatmentAction",
    "TreatmentDecision",
    "User",
    "UserSession",
]
