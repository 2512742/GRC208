"""Who may do what: one policy table (PLAN.md §2.1) plus record-level rules.

Two layers, both checked on the server for every request:
1. Role permissions: what a role may do at all (the table below).
2. Record rules: ownership ("own risks only"), assignment ("if assigned") and separation of
   duties (an approver never decides an acceptance for a risk they own or a request they made).

The CISO/CRO failover needs no special case: when the CISO owns a risk the SoD rule blocks the
CISO, and the CRO (also an approver, not the owner) remains eligible, and vice versa.

`authorize()` returns a Decision with a human-readable reason, which the API turns into a 403
plus a DENIED audit entry, and the UI shows on disabled buttons ("You own this risk").
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.models.enums import Role


class Perm(StrEnum):
    MANAGE_USERS = "manage_users"
    MANAGE_SETTINGS = "manage_settings"
    MANAGE_REGISTER = "manage_register"  # services, assets, obligations
    IMPORT_CSV = "import_csv"
    CREATE_RISK = "create_risk"
    EDIT_RISK = "edit_risk"  # all fields
    EDIT_OWN_RISK_LIMITED = "edit_own_risk_limited"  # description and review date only
    ASSESS_RISK = "assess_risk"  # initial assessment and reassessment
    DECIDE_TREATMENT = "decide_treatment"
    CREATE_ACTION = "create_action"
    UPDATE_ACTION = "update_action"  # progress and completion
    UPLOAD_EVIDENCE = "upload_evidence"
    REQUEST_ACCEPTANCE = "request_acceptance"
    DECIDE_ACCEPTANCE = "decide_acceptance"
    VIEW_ALL = "view_all"  # registers, records, evidence download
    EXPORT_REPORTS = "export_reports"
    VIEW_AUDIT = "view_audit"  # audit log and integrity check


P = Perm
READ_ONLY = frozenset({P.VIEW_ALL, P.EXPORT_REPORTS})

# Role-level policy: the §2.1 table. Record rules below narrow some of these further.
ROLE_PERMISSIONS: dict[Role, frozenset[Perm]] = {
    Role.ADMIN: READ_ONLY
    | {P.MANAGE_USERS, P.MANAGE_SETTINGS, P.MANAGE_REGISTER, P.IMPORT_CSV, P.VIEW_AUDIT},
    Role.ANALYST: READ_ONLY
    | {
        P.MANAGE_REGISTER,
        P.IMPORT_CSV,
        P.CREATE_RISK,
        P.EDIT_RISK,
        P.ASSESS_RISK,
        P.DECIDE_TREATMENT,
        P.CREATE_ACTION,
        P.UPDATE_ACTION,
        P.UPLOAD_EVIDENCE,
    },
    Role.OWNER: READ_ONLY
    | {
        P.EDIT_OWN_RISK_LIMITED,
        P.DECIDE_TREATMENT,
        P.CREATE_ACTION,
        P.UPDATE_ACTION,
        P.UPLOAD_EVIDENCE,
        P.REQUEST_ACCEPTANCE,
    },
    Role.APPROVER: READ_ONLY | {P.DECIDE_ACCEPTANCE, P.UPLOAD_EVIDENCE, P.VIEW_AUDIT},
    Role.AUDITOR: READ_ONLY | {P.VIEW_AUDIT},
}

# An approver may also own risks (the CISO owns R-015). As a risk owner they get the owner's
# record-level rights over *their own* risks, and nothing over anyone else's.
RISK_OWNER_EXTRA = frozenset(
    {P.EDIT_OWN_RISK_LIMITED, P.DECIDE_TREATMENT, P.CREATE_ACTION, P.REQUEST_ACCEPTANCE}
)


@dataclass(frozen=True)
class Actor:
    user_id: int
    role: Role
    is_active: bool = True


@dataclass(frozen=True)
class Target:
    """What the action is about. Fill in what applies; leave the rest None."""

    risk_owner_id: int | None = None
    action_owner_id: int | None = None
    acceptance_requested_by_id: int | None = None
    evidence_on: str | None = None  # "risk", "action", "acceptance", ... (EvidenceTarget value)


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str = ""

    def __bool__(self) -> bool:
        return self.allowed


ALLOW = Decision(True)


def deny(reason: str) -> Decision:
    return Decision(False, reason)


def role_permissions(role: Role) -> frozenset[Perm]:
    return ROLE_PERMISSIONS[role]


def authorize(actor: Actor, perm: Perm, target: Target | None = None) -> Decision:
    target = target or Target()
    if not actor.is_active:
        return deny("Your account is disabled.")

    owns_risk = target.risk_owner_id is not None and target.risk_owner_id == actor.user_id
    granted = perm in ROLE_PERMISSIONS[actor.role]
    if not granted and actor.role == Role.APPROVER and owns_risk and perm in RISK_OWNER_EXTRA:
        granted = True  # approver acting as the owner of their own risk
    if not granted:
        return deny(f"The {actor.role.value} role cannot do this.")

    # Analysts and admins work across the whole register; owners are limited to their records.
    if actor.role in (Role.OWNER, Role.APPROVER):
        decision = _owner_scope(actor, perm, target, owns_risk)
        if not decision:
            return decision

    if perm == P.DECIDE_ACCEPTANCE:
        return _separation_of_duties(actor, target)
    return ALLOW


def _owner_scope(actor: Actor, perm: Perm, target: Target, owns_risk: bool) -> Decision:
    if perm in RISK_OWNER_EXTRA and not owns_risk:
        return deny("You can only do this for risks you own.")
    if perm == P.UPDATE_ACTION:
        assigned = target.action_owner_id == actor.user_id
        if not assigned:
            return deny("Only the action's assigned owner (or an analyst) can update it.")
    if perm == P.UPLOAD_EVIDENCE:
        if actor.role == Role.APPROVER:
            if target.evidence_on != "acceptance" and not owns_risk:
                return deny("Approvers attach evidence to acceptance decisions only.")
        elif not (owns_risk or target.action_owner_id == actor.user_id):
            return deny("You can only attach evidence to your own risks or assigned actions.")
    return ALLOW


def _separation_of_duties(actor: Actor, target: Target) -> Decision:
    if target.risk_owner_id is None or target.acceptance_requested_by_id is None:
        return deny("The risk owner and requester must be known to decide an acceptance.")
    if target.risk_owner_id == actor.user_id:
        return deny("You own this risk, so another approver must decide.")
    if target.acceptance_requested_by_id == actor.user_id:
        return deny("You requested this acceptance, so another approver must decide.")
    return ALLOW
