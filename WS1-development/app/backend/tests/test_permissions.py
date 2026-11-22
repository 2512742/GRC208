"""P2 permissions: every row of the §2.1 table, ownership scope, and separation of duties.

Unit level for T12 (owner can't approve own), T14 (CISO/CRO failover), T19 (auditor read-only)
and T20 (analyst can't approve). P3-P5 repeat them through the API.
"""

from __future__ import annotations

import pytest

from app.core.permissions import (
    ROLE_PERMISSIONS,
    Actor,
    Perm,
    Target,
    authorize,
)
from app.models.enums import Role

# Personas from the demo data (ids are arbitrary).
OMOTAYO = Actor(1, Role.ANALYST)
EMMANUEL = Actor(2, Role.OWNER)
ANITA = Actor(3, Role.OWNER)
ADEOLA_CISO = Actor(4, Role.APPROVER)
KELECHI_CRO = Actor(5, Role.APPROVER)
ERNESTINA = Actor(6, Role.AUDITOR)
ADMIN = Actor(7, Role.ADMIN)

WRITE_PERMS = set(Perm) - {Perm.VIEW_ALL, Perm.EXPORT_REPORTS, Perm.VIEW_AUDIT}

# The §2.1 table, restated independently: role -> permissions it holds at role level.
EXPECTED = {
    Role.ADMIN: {
        "manage_users",
        "manage_settings",
        "manage_register",
        "import_csv",
        "view_all",
        "export_reports",
        "view_audit",
    },
    Role.ANALYST: {
        "manage_register",
        "import_csv",
        "create_risk",
        "edit_risk",
        "assess_risk",
        "decide_treatment",
        "create_action",
        "update_action",
        "upload_evidence",
        "view_all",
        "export_reports",
    },
    Role.OWNER: {
        "edit_own_risk_limited",
        "decide_treatment",
        "create_action",
        "update_action",
        "upload_evidence",
        "request_acceptance",
        "view_all",
        "export_reports",
    },
    Role.APPROVER: {
        "decide_acceptance",
        "upload_evidence",
        "view_all",
        "export_reports",
        "view_audit",
    },
    Role.AUDITOR: {"view_all", "export_reports", "view_audit"},
}


@pytest.mark.parametrize("role", list(Role))
def test_role_table_matches_plan(role: Role) -> None:
    assert {p.value for p in ROLE_PERMISSIONS[role]} == EXPECTED[role]


@pytest.mark.parametrize("perm", sorted(WRITE_PERMS))
def test_t19_auditor_can_change_nothing(perm: Perm) -> None:
    decision = authorize(
        ERNESTINA, perm, Target(risk_owner_id=6, action_owner_id=6, acceptance_requested_by_id=2)
    )
    assert not decision
    assert "auditor role cannot" in decision.reason


def test_everyone_can_view_and_export() -> None:
    for actor in (OMOTAYO, EMMANUEL, ADEOLA_CISO, ERNESTINA, ADMIN):
        assert authorize(actor, Perm.VIEW_ALL)
        assert authorize(actor, Perm.EXPORT_REPORTS)


def test_only_admin_approver_auditor_see_the_audit_log() -> None:
    assert authorize(ADMIN, Perm.VIEW_AUDIT)
    assert authorize(ADEOLA_CISO, Perm.VIEW_AUDIT)
    assert authorize(ERNESTINA, Perm.VIEW_AUDIT)
    assert not authorize(OMOTAYO, Perm.VIEW_AUDIT)
    assert not authorize(EMMANUEL, Perm.VIEW_AUDIT)


def test_disabled_accounts_can_do_nothing() -> None:
    assert not authorize(Actor(1, Role.ANALYST, is_active=False), Perm.VIEW_ALL)


# ── Ownership scope ────────────────────────────────────────────────────────────────────────

EMMANUELS_RISK = Target(risk_owner_id=EMMANUEL.user_id)
ANITAS_RISK = Target(risk_owner_id=ANITA.user_id)


@pytest.mark.parametrize(
    "perm",
    [
        Perm.EDIT_OWN_RISK_LIMITED,
        Perm.DECIDE_TREATMENT,
        Perm.CREATE_ACTION,
        Perm.REQUEST_ACCEPTANCE,
    ],
)
def test_owner_acts_on_own_risks_only(perm: Perm) -> None:
    assert authorize(EMMANUEL, perm, EMMANUELS_RISK)
    refused = authorize(EMMANUEL, perm, ANITAS_RISK)
    assert not refused and "risks you own" in refused.reason


def test_owner_cannot_assess_or_fully_edit_even_own_risk() -> None:
    assert not authorize(EMMANUEL, Perm.ASSESS_RISK, EMMANUELS_RISK)
    assert not authorize(EMMANUEL, Perm.EDIT_RISK, EMMANUELS_RISK)
    assert not authorize(EMMANUEL, Perm.CREATE_RISK)


def test_t21_owner_updates_only_actions_assigned_to_them() -> None:
    assert authorize(EMMANUEL, Perm.UPDATE_ACTION, Target(action_owner_id=EMMANUEL.user_id))
    refused = authorize(EMMANUEL, Perm.UPDATE_ACTION, Target(action_owner_id=ANITA.user_id))
    assert not refused and "assigned owner" in refused.reason


def test_owner_evidence_on_own_risk_or_assigned_action_only() -> None:
    assert authorize(EMMANUEL, Perm.UPLOAD_EVIDENCE, EMMANUELS_RISK)
    assert authorize(
        EMMANUEL,
        Perm.UPLOAD_EVIDENCE,
        Target(risk_owner_id=ANITA.user_id, action_owner_id=EMMANUEL.user_id),
    )
    assert not authorize(EMMANUEL, Perm.UPLOAD_EVIDENCE, ANITAS_RISK)


def test_analyst_works_across_the_register() -> None:
    for perm in (
        Perm.CREATE_RISK,
        Perm.EDIT_RISK,
        Perm.ASSESS_RISK,
        Perm.CREATE_ACTION,
        Perm.UPDATE_ACTION,
        Perm.UPLOAD_EVIDENCE,
    ):
        assert authorize(OMOTAYO, perm, ANITAS_RISK)


def test_only_admin_manages_users_and_settings() -> None:
    for actor in (OMOTAYO, EMMANUEL, KELECHI_CRO, ERNESTINA):
        assert not authorize(actor, Perm.MANAGE_USERS)
        assert not authorize(actor, Perm.MANAGE_SETTINGS)
    assert authorize(ADMIN, Perm.MANAGE_USERS) and authorize(ADMIN, Perm.MANAGE_SETTINGS)


def test_admin_cannot_assess_or_approve() -> None:
    assert not authorize(ADMIN, Perm.ASSESS_RISK)
    assert not authorize(
        ADMIN, Perm.DECIDE_ACCEPTANCE, Target(risk_owner_id=2, acceptance_requested_by_id=2)
    )


# ── Separation of duties on acceptance ─────────────────────────────────────────────────────


def acceptance(owner: Actor, requester: Actor | None = None) -> Target:
    return Target(
        risk_owner_id=owner.user_id, acceptance_requested_by_id=(requester or owner).user_id
    )


def test_t13_a_different_approver_can_decide() -> None:
    assert authorize(KELECHI_CRO, Perm.DECIDE_ACCEPTANCE, acceptance(EMMANUEL))
    assert authorize(ADEOLA_CISO, Perm.DECIDE_ACCEPTANCE, acceptance(EMMANUEL))


def test_t12_owner_role_can_never_decide_acceptance() -> None:
    refused = authorize(EMMANUEL, Perm.DECIDE_ACCEPTANCE, acceptance(EMMANUEL))
    assert not refused and "owner role cannot" in refused.reason


def test_t20_analyst_cannot_decide_acceptance() -> None:
    assert not authorize(OMOTAYO, Perm.DECIDE_ACCEPTANCE, acceptance(EMMANUEL))


def test_t14_ciso_owned_risk_blocks_ciso_and_leaves_cro_eligible() -> None:
    r015 = acceptance(ADEOLA_CISO)  # the CISO owns R-015 and requested its acceptance
    refused = authorize(ADEOLA_CISO, Perm.DECIDE_ACCEPTANCE, r015)
    assert not refused and refused.reason == "You own this risk, so another approver must decide."
    assert authorize(KELECHI_CRO, Perm.DECIDE_ACCEPTANCE, r015)


def test_cro_owned_risk_blocks_cro_and_leaves_ciso_eligible() -> None:
    target = acceptance(KELECHI_CRO)
    assert not authorize(KELECHI_CRO, Perm.DECIDE_ACCEPTANCE, target)
    assert authorize(ADEOLA_CISO, Perm.DECIDE_ACCEPTANCE, target)


def test_approver_who_requested_cannot_decide_even_if_not_owner() -> None:
    refused = authorize(KELECHI_CRO, Perm.DECIDE_ACCEPTANCE, acceptance(EMMANUEL, KELECHI_CRO))
    assert not refused and "You requested this acceptance" in refused.reason


def test_decision_refused_when_owner_or_requester_unknown() -> None:
    assert not authorize(KELECHI_CRO, Perm.DECIDE_ACCEPTANCE, Target())


def test_approver_as_risk_owner_gets_owner_rights_on_own_risk_only() -> None:
    own = Target(risk_owner_id=ADEOLA_CISO.user_id)
    assert authorize(ADEOLA_CISO, Perm.REQUEST_ACCEPTANCE, own)
    assert authorize(ADEOLA_CISO, Perm.CREATE_ACTION, own)
    assert authorize(ADEOLA_CISO, Perm.UPLOAD_EVIDENCE, own)
    assert not authorize(ADEOLA_CISO, Perm.REQUEST_ACCEPTANCE, EMMANUELS_RISK)
    assert not authorize(ADEOLA_CISO, Perm.CREATE_ACTION, EMMANUELS_RISK)


def test_approver_evidence_only_on_acceptance_decisions_otherwise() -> None:
    assert authorize(
        KELECHI_CRO, Perm.UPLOAD_EVIDENCE, Target(risk_owner_id=2, evidence_on="acceptance")
    )
    assert not authorize(
        KELECHI_CRO, Perm.UPLOAD_EVIDENCE, Target(risk_owner_id=2, evidence_on="action")
    )
