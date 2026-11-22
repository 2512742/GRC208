"""Allowed values. Each enum is mirrored by a CHECK constraint in the database."""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    ANALYST = "analyst"
    OWNER = "owner"
    APPROVER = "approver"
    AUDITOR = "auditor"


class AssetType(StrEnum):
    APPLICATION = "application"
    API = "api"
    DATABASE = "database"
    SAAS = "saas"
    ENDPOINT = "endpoint"
    NETWORK = "network"
    DATA_STORE = "data_store"
    THIRD_PARTY_SERVICE = "third_party_service"


class Classification(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class AssetStatus(StrEnum):
    ACTIVE = "active"
    RETIRED = "retired"


class Regime(StrEnum):
    NDPA_2023 = "NDPA-2023"
    CBN = "CBN"
    SEC_NG = "SEC-NG"
    PCI_DSS_4 = "PCI-DSS-4.0"


class Framework(StrEnum):
    NIST_CSF_2 = "NIST-CSF-2.0"
    ISO_27001_2022 = "ISO-27001-2022"
    CIS_8_1 = "CIS-8.1"


class RiskStatus(StrEnum):
    """Stored states. 'Acceptance expired' is computed at read time, never stored."""

    OPEN = "open"
    TREATMENT_IN_PROGRESS = "treatment_in_progress"
    AWAITING_REASSESSMENT = "awaiting_reassessment"
    ACCEPTED = "accepted"
    CLOSED = "closed"


class AssessmentType(StrEnum):
    INITIAL = "initial"
    REASSESSMENT = "reassessment"


class Band(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Strategy(StrEnum):
    REDUCE = "reduce"
    ACCEPT = "accept"
    TRANSFER = "transfer"
    AVOID = "avoid"


class ActionStatus(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AcceptanceStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class EvidenceTarget(StrEnum):
    RISK = "risk"
    ASSESSMENT = "assessment"
    DECISION = "decision"
    ACTION = "action"
    ACCEPTANCE = "acceptance"
    IMPORT_BATCH = "import_batch"


class AuditAction(StrEnum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    ASSESS = "ASSESS"
    COMPLETE = "COMPLETE"
    UPLOAD = "UPLOAD"
    REQUEST = "REQUEST"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    IMPORT = "IMPORT"
    EXPORT = "EXPORT"
    LOGIN = "LOGIN"
    LOGIN_FAILED = "LOGIN_FAILED"
    LOGOUT = "LOGOUT"
    DENIED = "DENIED"
    SETTING = "SETTING"


class ImportType(StrEnum):
    ASSETS = "assets"
    RISKS = "risks"


class ImportStatus(StrEnum):
    PREVIEWED = "previewed"
    COMMITTED = "committed"
    CANCELLED = "cancelled"
