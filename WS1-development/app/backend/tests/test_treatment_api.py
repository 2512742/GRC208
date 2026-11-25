"""P5: treatment, evidence, reassessment and acceptance through the API (T06-T16, T20, T21,
T27, T28), ending with the brief's whole required demonstration as one scripted scenario."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, col, select

from app.models import AuditLog, RiskAssessment
from app.services import clock
from tests.conftest import sign_in

PDF = b"%PDF-1.7\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
EXE = b"MZ\x90\x00" + b"\x00" * 60
# Deadlines are judged in The Alajo's zone (WAT), not this machine's: between midnight and
# 02:00 EAT the two dates differ, so take "today" the way the app does.
TODAY = datetime.now(ZoneInfo("Africa/Lagos")).date()


def pdf(name: str = "proof.pdf", content: bytes = PDF) -> dict:
    return {"file": (name, content, "application/pdf")}


def as_user(api: TestClient, who: str) -> None:
    api.cookies.clear()
    sign_in(api, who)


def last_audit(db: Session, action: str | None = None) -> AuditLog:
    query = select(AuditLog).order_by(col(AuditLog.id).desc())
    if action:
        query = query.where(AuditLog.action == action)
    return db.exec(query).first()  # type: ignore[return-value]


@pytest.fixture
def world(api: TestClient, people: dict) -> dict:
    """One service, one asset, two risks (Emmanuel's L4xI5 and the CISO's), as Omotayo."""
    sign_in(api, "omotayo")
    service = api.post("/api/services", json={"code": "S1", "name": "Savings and Wallets"}).json()
    asset = api.post(
        "/api/assets",
        json={"name": "Wallet ledger", "asset_type": "database", "service_id": service["id"]},
    ).json()

    def risk(owner: str, title: str, likelihood: int, impact: int) -> dict:
        body = {
            "title": title,
            "description": "d",
            "threat": "t",
            "vulnerability": "v",
            "business_impact": "i",
            "owner_id": people[owner].id,
            "asset_ids": [asset["id"]],
            "initial_assessment": {
                "likelihood": likelihood,
                "impact": impact,
                "rationale": "Initial scoring for the test scenario.",
            },
        }
        response = api.post("/api/risks", json=body)
        assert response.status_code == 201, response.text
        return response.json()

    return {
        "asset": asset,
        "r1": risk("emmanuel", "Ledger double-spend race condition", 4, 5),
        "r_ciso": risk("adeola", "Privileged insider ledger manipulation", 2, 5),
    }


def new_action(api: TestClient, risk: dict, owner_id: int, **extra: object) -> dict:
    body = {
        "title": "Add row locking and idempotency keys",
        "owner_id": owner_id,
        "estimated_cost_ngn": "2500000.00",
        **extra,
    }
    response = api.post(f"/api/risks/{risk['id']}/actions", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def acceptance_body(days: int = 90, text: str | None = None) -> dict:
    return {
        "justification": text
        or "Compensating controls are in place and the cost of full "
        "remediation exceeds the expected loss this year.",
        "proposed_expiry": (TODAY + timedelta(days=days)).isoformat(),
    }


# ── Decisions and actions (T06) ────────────────────────────────────────────────────────────


def test_decision_with_target_residual(api: TestClient, world: dict) -> None:
    response = api.post(
        f"/api/risks/{world['r1']['id']}/decisions",
        json={
            "strategy": "reduce",
            "justification": "Engineering fix is cheap and effective.",
            "target_likelihood": 1,
            "target_impact": 5,
        },
    )
    assert response.status_code == 201
    assert response.json()["target_score"] == 5
    risk = api.get(f"/api/risks/{world['r1']['id']}").json()
    assert risk["strategy"] == "reduce" and risk["current"]["score"] == 20  # target isn't the score
    half = {"strategy": "reduce", "justification": "Only one target given.", "target_impact": 2}
    assert api.post(f"/api/risks/{world['r1']['id']}/decisions", json=half).status_code == 422


def test_t06_action_saved_with_sla_due_date_and_listed_for_owner(
    api: TestClient, world: dict, people: dict
) -> None:
    action = new_action(api, world["r1"], people["emmanuel"].id)
    assert action["action_code"] == "T-001" and action["status"] == "not_started"
    assert action["due_date"] == (TODAY + timedelta(days=30)).isoformat()  # Critical SLA
    assert action["estimated_cost_ngn"] == "2500000.00"
    risk = api.get(f"/api/risks/{world['r1']['id']}").json()
    assert risk["status"] == "treatment_in_progress" and risk["open_actions"] == 1
    as_user(api, "emmanuel")
    mine = api.get("/api/actions", params={"mine": True}).json()
    assert [a["action_code"] for a in mine] == ["T-001"] and mine[0]["can_update"] is True


def test_action_rules(api: TestClient, world: dict, people: dict) -> None:
    past = {
        "title": "Backdated action",
        "owner_id": people["emmanuel"].id,
        "due_date": (TODAY - timedelta(days=1)).isoformat(),
    }
    assert api.post(f"/api/risks/{world['r1']['id']}/actions", json=past).status_code == 422
    bad_owner = {"title": "Owned by nobody", "owner_id": 999999}
    assert api.post(f"/api/risks/{world['r1']['id']}/actions", json=bad_owner).status_code == 422
    negative = {
        "title": "Negative cost",
        "owner_id": people["emmanuel"].id,
        "estimated_cost_ngn": "-5",
    }
    assert api.post(f"/api/risks/{world['r1']['id']}/actions", json=negative).status_code == 422


def test_owner_creates_actions_on_own_risk_only(api: TestClient, world: dict, people: dict) -> None:
    as_user(api, "emmanuel")
    new_action(api, world["r1"], people["emmanuel"].id)
    body = {"title": "Not my risk to treat", "owner_id": people["emmanuel"].id}
    assert api.post(f"/api/risks/{world['r_ciso']['id']}/actions", json=body).status_code == 403


def test_t21_assignee_updates_progress_but_not_the_plan(
    api: TestClient, world: dict, people: dict
) -> None:
    action = new_action(api, world["r1"], people["anita"].id)  # assigned to Anita
    as_user(api, "anita")
    ok = api.patch(
        f"/api/actions/{action['id']}",
        json={"status": "in_progress", "description": "Started on staging."},
    )
    assert ok.status_code == 200 and ok.json()["status"] == "in_progress"
    later = (TODAY + timedelta(days=200)).isoformat()
    moved = api.patch(f"/api/actions/{action['id']}", json={"due_date": later})
    assert moved.status_code == 403 and "due_date" in moved.json()["detail"]
    as_user(api, "kelechi")  # neither risk owner nor assignee
    assert api.patch(f"/api/actions/{action['id']}", json={"description": "x"}).status_code == 403


def test_cancelling_the_last_action_reopens_the_risk(
    api: TestClient, world: dict, people: dict
) -> None:
    action = new_action(api, world["r1"], people["emmanuel"].id)
    assert (
        api.patch(f"/api/actions/{action['id']}", json={"status": "cancelled"}).status_code == 200
    )
    assert api.get(f"/api/risks/{world['r1']['id']}").json()["status"] == "open"
    again = api.patch(f"/api/actions/{action['id']}", json={"description": "too late"})
    assert again.status_code == 409


def test_status_completed_cannot_be_set_by_patch(
    api: TestClient, world: dict, people: dict
) -> None:
    action = new_action(api, world["r1"], people["emmanuel"].id)
    assert (
        api.patch(f"/api/actions/{action['id']}", json={"status": "completed"}).status_code == 422
    )


def test_action_controls_linked(api: TestClient, world: dict, people: dict, db: Session) -> None:
    from app.services.reference_data import load_reference_data

    load_reference_data(db)
    controls = api.get("/api/controls", params={"framework": "NIST-CSF-2.0"}).json()[:2]
    action = new_action(
        api, world["r1"], people["emmanuel"].id, control_ids=[c["id"] for c in controls]
    )
    assert len(action["controls"]) == 2
    updated = api.patch(f"/api/actions/{action['id']}", json={"control_ids": [controls[0]["id"]]})
    assert [c["control_ref"] for c in updated.json()["controls"]] == [controls[0]["control_ref"]]


# ── Completion (T07, T08) ──────────────────────────────────────────────────────────────────


def test_t07_completion_without_evidence_rejected(
    api: TestClient, world: dict, people: dict
) -> None:
    action = new_action(api, world["r1"], people["emmanuel"].id)
    url = f"/api/actions/{action['id']}/complete"
    assert api.post(url, data={"note": "Deployed the fix to production."}).status_code == 422
    assert api.post(url, data={"note": "short"}, files=pdf()).status_code == 422
    exe = api.post(
        url,
        data={"note": "Deployed the fix to production."},
        files={"file": ("proof.pdf", EXE, "application/pdf")},
    )
    assert exe.status_code == 422 and "not a valid PDF" in exe.json()["detail"]
    assert api.get(f"/api/actions/{action['id']}").json()["status"] == "not_started"


def test_t08_completion_keeps_the_score_and_awaits_reassessment(
    api: TestClient, world: dict, people: dict, db: Session
) -> None:
    action = new_action(api, world["r1"], people["emmanuel"].id)
    as_user(api, "emmanuel")
    done = api.post(
        f"/api/actions/{action['id']}/complete",
        data={"note": "Row locking deployed and load-tested."},
        files=pdf(),
    )
    assert done.status_code == 200, done.text
    body = done.json()
    assert body["status"] == "completed" and body["evidence_count"] == 1
    assert body["completed_by"]["full_name"] == "Emmanuel Teye Adjei"
    risk = api.get(f"/api/risks/{world['r1']['id']}").json()
    assert risk["status"] == "awaiting_reassessment"
    assert risk["current"]["score"] == 20  # unchanged
    assert len(risk["assessments"]) == 1
    entry = last_audit(db, "COMPLETE")
    assert entry.after["sha256"] and entry.username == "emmanuel"  # type: ignore[index]
    again = api.post(
        f"/api/actions/{action['id']}/complete",
        data={"note": "Trying to complete twice."},
        files=pdf(),
    )
    assert again.status_code == 409


# ── Reassessment (T09, T10) ────────────────────────────────────────────────────────────────


def reassess(
    api: TestClient,
    risk: dict,
    likelihood: int = 1,
    impact: int = 5,
    files: dict | None = None,
    **extra: object,
):  # type: ignore[no-untyped-def]
    data = {
        "likelihood": likelihood,
        "impact": impact,
        "rationale": "Load test after the fix shows no double-spend.",
        **extra,
    }
    return api.post(
        f"/api/risks/{risk['id']}/reassessments",
        data=data,
        files=pdf("loadtest.pdf") if files is None else files,
    )


def test_t09_reassessment_needs_evidence_and_rationale(api: TestClient, world: dict) -> None:
    no_file = api.post(
        f"/api/risks/{world['r1']['id']}/reassessments",
        data={"likelihood": 1, "impact": 5, "rationale": "Fixed and verified now."},
    )
    assert no_file.status_code == 422
    assert reassess(api, world["r1"], rationale="short").status_code == 422
    assert reassess(api, world["r1"], likelihood=6).status_code == 422
    as_user(api, "emmanuel")  # owners don't assess
    assert reassess(api, world["r1"]).status_code == 403


def test_t10_valid_reassessment_adds_a_row_and_keeps_the_original(
    api: TestClient, world: dict, people: dict, db: Session
) -> None:
    action = new_action(api, world["r1"], people["emmanuel"].id)
    api.post(
        f"/api/actions/{action['id']}/complete",
        data={"note": "Row locking deployed and load-tested."},
        files=pdf(),
    )
    response = reassess(api, world["r1"], 1, 5)
    assert response.status_code == 201, response.text
    body = response.json()
    assert (body["score"], body["band"], body["above_appetite"]) == (5, "medium", False)
    assert body["original_score"] == 20 and body["risk_status"] == "open"
    assert body["evidence"]["target_type"] == "assessment"
    risk = api.get(f"/api/risks/{world['r1']['id']}").json()
    assert [a["score"] for a in risk["assessments"]] == [20, 5]
    assert [a["assessment_type"] for a in risk["assessments"]] == ["initial", "reassessment"]
    assert risk["original_score"] == 20 and risk["current"]["score"] == 5
    rows = db.exec(select(RiskAssessment).where(RiskAssessment.risk_id == world["r1"]["id"])).all()
    assert len(rows) == 2


def test_closing_needs_an_avoid_decision(api: TestClient, world: dict) -> None:
    refused = reassess(api, world["r1"], close_risk=True)
    assert refused.status_code == 409 and "avoid" in refused.json()["detail"]
    api.post(
        f"/api/risks/{world['r1']['id']}/decisions",
        json={"strategy": "avoid", "justification": "Decommission the legacy ledger API."},
    )
    closed = reassess(api, world["r1"], close_risk=True)
    assert closed.status_code == 201 and closed.json()["risk_status"] == "closed"
    body = {"title": "Too late now", "owner_id": world["r1"]["owner"]["id"]}
    assert api.post(f"/api/risks/{world['r1']['id']}/actions", json=body).status_code == 409


# ── Acceptance (T12-T16, T20) ──────────────────────────────────────────────────────────────


def test_t12_owner_cannot_approve_own_request_and_attempt_is_audited(
    api: TestClient, world: dict, db: Session
) -> None:
    as_user(api, "emmanuel")
    request = api.post(f"/api/risks/{world['r1']['id']}/acceptances", json=acceptance_body())
    assert request.status_code == 201
    decision = {"decision": "approve", "comment": "Approving my own risk, why not."}
    refused = api.post(f"/api/acceptances/{request.json()['id']}/decision", json=decision)
    assert refused.status_code == 403
    entry = last_audit(db, "DENIED")
    assert entry.username == "emmanuel" and entry.object_type == "acceptance"


def test_t13_different_approver_approves_with_dates(
    api: TestClient, world: dict, db: Session
) -> None:
    as_user(api, "emmanuel")
    request = api.post(
        f"/api/risks/{world['r1']['id']}/acceptances", json=acceptance_body(120)
    ).json()
    assert request["can_decide"] is False and "owner role cannot" in request["cannot_decide_reason"]
    as_user(api, "kelechi")
    queue = api.get("/api/acceptances", params={"status": "pending"}).json()
    assert queue[0]["can_decide"] is True and queue[0]["cannot_decide_reason"] is None
    expiry = (TODAY + timedelta(days=90)).isoformat()
    approved = api.post(
        f"/api/acceptances/{request['id']}/decision",
        json={
            "decision": "approve",
            "comment": "Compensating controls verified by the CRO office.",
            "expiry_date": expiry,
        },
    )
    assert approved.status_code == 200
    body = approved.json()
    assert body["status"] == "approved" and body["expiry_date"] == expiry
    assert body["decided_by"]["full_name"] == "Kelechi Kenneth Nwankwo"
    assert body["decision_date"] is not None and body["cannot_decide_reason"] == "Already approved."
    assert api.get(f"/api/risks/{world['r1']['id']}").json()["status"] == "accepted"
    assert last_audit(db, "APPROVE").username == "kelechi"


def test_t14_ciso_owned_risk_only_cro_may_decide(api: TestClient, world: dict) -> None:
    as_user(api, "adeola")  # the CISO owns this risk and requests acceptance
    request = api.post(
        f"/api/risks/{world['r_ciso']['id']}/acceptances", json=acceptance_body()
    ).json()
    assert request["cannot_decide_reason"] == "You own this risk, so another approver must decide."
    decision = {"decision": "approve", "comment": "Dual control is in place for DB access."}
    assert api.post(f"/api/acceptances/{request['id']}/decision", json=decision).status_code == 403
    as_user(api, "kelechi")
    assert api.post(f"/api/acceptances/{request['id']}/decision", json=decision).status_code == 200


def test_t20_analyst_and_auditor_cannot_decide(api: TestClient, world: dict) -> None:
    as_user(api, "emmanuel")
    request = api.post(f"/api/risks/{world['r1']['id']}/acceptances", json=acceptance_body()).json()
    decision = {"decision": "approve", "comment": "I am not an approver at all."}
    for who in ("omotayo", "ernestina", "admin"):
        as_user(api, who)
        assert (
            api.post(f"/api/acceptances/{request['id']}/decision", json=decision).status_code == 403
        )


def test_t15_acceptance_request_rules(api: TestClient, world: dict, people: dict) -> None:
    as_user(api, "emmanuel")
    url = f"/api/risks/{world['r1']['id']}/acceptances"
    assert api.post(url, json=acceptance_body(text="Too short to justify.")).status_code == 422
    assert api.post(url, json=acceptance_body(days=-1)).status_code == 422
    assert api.post(url, json=acceptance_body(days=0)).status_code == 422
    assert api.post(url, json=acceptance_body(days=366)).status_code == 422
    assert api.post(url, json=acceptance_body(days=365)).status_code == 201
    assert api.post(url, json=acceptance_body()).status_code == 409  # one pending at a time
    as_user(api, "anita")  # not the owner
    assert api.post(url, json=acceptance_body()).status_code == 403


def test_decision_rules(api: TestClient, world: dict) -> None:
    as_user(api, "emmanuel")
    request = api.post(f"/api/risks/{world['r1']['id']}/acceptances", json=acceptance_body()).json()
    as_user(api, "kelechi")
    url = f"/api/acceptances/{request['id']}/decision"
    assert api.post(url, json={"decision": "approve", "comment": "ok"}).status_code == 422
    too_far = (TODAY + timedelta(days=400)).isoformat()
    assert (
        api.post(
            url,
            json={
                "decision": "approve",
                "comment": "Approved for a long time.",
                "expiry_date": too_far,
            },
        ).status_code
        == 422
    )
    rejected = api.post(url, json={"decision": "reject", "comment": "Treat it: the fix is cheap."})
    assert rejected.status_code == 200 and rejected.json()["status"] == "rejected"
    assert rejected.json()["expiry_date"] is None
    assert (
        api.post(url, json={"decision": "approve", "comment": "Changed my mind now."}).status_code
        == 409
    )
    assert api.get(f"/api/risks/{world['r1']['id']}").json()["status"] == "open"


def test_t16_expired_acceptance_flagged_for_review(api: TestClient, world: dict) -> None:
    as_user(api, "emmanuel")
    request = api.post(
        f"/api/risks/{world['r1']['id']}/acceptances", json=acceptance_body(30)
    ).json()
    as_user(api, "kelechi")
    api.post(
        f"/api/acceptances/{request['id']}/decision",
        json={"decision": "approve", "comment": "Short acceptance while vendor fixes it."},
    )
    later = datetime.combine(TODAY + timedelta(days=32), datetime.min.time(), tzinfo=UTC)
    with clock.frozen(later):
        as_user(api, "kelechi")  # a month later: the old session has (correctly) expired
        expired = api.get("/api/acceptances", params={"expired": True}).json()
        assert [a["id"] for a in expired] == [request["id"]]
        risk = api.get(f"/api/risks/{world['r1']['id']}").json()
        assert risk["status"] == "accepted" and risk["display_status"] == "acceptance_expired"
    current = api.get(f"/api/risks/{world['r1']['id']}").json()
    assert current["display_status"] == "accepted"  # still valid today


def test_cannot_accept_an_unscored_risk(api: TestClient, world: dict, people: dict) -> None:
    body = {
        "title": "Unscored risk for acceptance",
        "description": "d",
        "threat": "t",
        "vulnerability": "v",
        "business_impact": "i",
        "owner_id": people["emmanuel"].id,
        "asset_ids": [world["asset"]["id"]],
    }
    risk = api.post("/api/risks", json=body).json()
    as_user(api, "emmanuel")
    assert (
        api.post(f"/api/risks/{risk['id']}/acceptances", json=acceptance_body()).status_code == 409
    )


# ── Overdue ────────────────────────────────────────────────────────────────────────────────


def test_overdue_actions_listed_first_with_days(api: TestClient, world: dict, people: dict) -> None:
    soon = new_action(
        api, world["r1"], people["emmanuel"].id, due_date=(TODAY + timedelta(days=5)).isoformat()
    )
    later = new_action(
        api,
        world["r1"],
        people["emmanuel"].id,
        title="Second action here",
        due_date=(TODAY + timedelta(days=60)).isoformat(),
    )
    future = datetime.combine(TODAY + timedelta(days=8), datetime.min.time(), tzinfo=UTC)
    with clock.frozen(future + timedelta(hours=12)):
        as_user(api, "omotayo")  # days later: sign in again
        overdue = api.get("/api/actions", params={"overdue": True}).json()
        assert [(a["id"], a["days_overdue"]) for a in overdue] == [(soon["id"], 3)]
        listed = api.get("/api/actions").json()
        assert listed[0]["id"] == soon["id"] and listed[0]["overdue"] is True
        assert api.get("/api/actions", params={"overdue": False}).json()[0]["id"] == later["id"]
        risk = api.get(f"/api/risks/{world['r1']['id']}").json()
        assert (risk["open_actions"], risk["overdue_actions"]) == (2, 1)


# ── Evidence (T27, T28) ────────────────────────────────────────────────────────────────────


def test_t28_download_requires_sign_in_and_is_an_attachment(api: TestClient, world: dict) -> None:
    uploaded = api.post(
        "/api/evidence",
        data={
            "target_type": "risk",
            "target_id": world["r1"]["id"],
            "description": "Pen test report",
        },
        files=pdf("Pen test – Q4.pdf"),
    ).json()
    response = api.get(uploaded["download_url"])
    assert response.status_code == 200 and response.content == PDF
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].startswith("attachment;")
    assert (
        "filename*=UTF-8''Pen%20test%20%E2%80%93%20Q4.pdf"
        in response.headers["content-disposition"]
    )
    assert response.headers["x-evidence-sha256"] == uploaded["sha256"]
    assert "sandbox" in response.headers["content-security-policy"]
    api.cookies.clear()
    assert api.get(uploaded["download_url"]).status_code == 401


def test_t27_bad_uploads_rejected(api: TestClient, world: dict) -> None:
    form = {"target_type": "risk", "target_id": world["r1"]["id"]}
    exe = api.post(
        "/api/evidence", data=form, files={"file": ("tool.exe", EXE, "application/x-msdownload")}
    )
    assert exe.status_code == 422 and "not allowed" in exe.json()["detail"]
    big = PDF + b"0" * (4 * 1024 * 1024)
    assert api.post("/api/evidence", data=form, files=pdf("big.pdf", big)).status_code == 422
    missing = api.post(
        "/api/evidence", data={"target_type": "risk", "target_id": 999999}, files=pdf()
    )
    assert missing.status_code == 404


def test_supersede_instead_of_edit(api: TestClient, world: dict, people: dict) -> None:
    form = {"target_type": "risk", "target_id": world["r1"]["id"]}
    first = api.post("/api/evidence", data=form, files=pdf("v1.pdf")).json()
    second = api.post(
        "/api/evidence", data={**form, "supersedes_id": first["id"]}, files=pdf("v2.pdf")
    ).json()
    listed = api.get("/api/evidence", params=form).json()
    assert [(e["original_name"], e["superseded_by_id"]) for e in listed] == [
        ("v1.pdf", second["id"]),
        ("v2.pdf", None),
    ]
    other = {
        "target_type": "risk",
        "target_id": world["r_ciso"]["id"],
        "supersedes_id": first["id"],
    }
    assert api.post("/api/evidence", data=other, files=pdf()).status_code == 422
    assert api.delete(f"/api/evidence/{first['id']}").status_code in (404, 405)  # no such route


def test_evidence_upload_permissions(api: TestClient, world: dict) -> None:
    form = {"target_type": "risk", "target_id": world["r1"]["id"]}
    as_user(api, "ernestina")
    assert api.post("/api/evidence", data=form, files=pdf()).status_code == 403
    as_user(api, "anita")  # not her risk
    assert api.post("/api/evidence", data=form, files=pdf()).status_code == 403
    as_user(api, "emmanuel")
    request = api.post(f"/api/risks/{world['r1']['id']}/acceptances", json=acceptance_body()).json()
    as_user(api, "kelechi")  # approvers attach evidence to acceptance decisions
    on_acceptance = {"target_type": "acceptance", "target_id": request["id"]}
    assert api.post("/api/evidence", data=on_acceptance, files=pdf()).status_code == 201
    assert api.post("/api/evidence", data=form, files=pdf()).status_code == 403
    imports = {"target_type": "import_batch", "target_id": 1}
    assert api.post("/api/evidence", data=imports, files=pdf()).status_code == 422


# ── The brief's required demonstration, end to end ────────────────────────────────────────


def test_brief_required_demonstration(api: TestClient, people: dict, db: Session) -> None:
    sign_in(api, "omotayo")
    service = api.post("/api/services", json={"code": "S1", "name": "Savings and Wallets"}).json()
    asset = api.post(
        "/api/assets",
        json={
            "name": "Payment gateway integration",
            "asset_type": "api",
            "service_id": service["id"],
        },
    ).json()

    # 1. Create a risk with likelihood 4 and impact 5, producing a score of 20.
    risk = api.post(
        "/api/risks",
        json={
            "title": "Fake deposits via spoofed payment webhooks",
            "description": "d",
            "threat": "Forged settlement webhooks",
            "vulnerability": "No signature verification",
            "business_impact": "Unbacked wallet credits",
            "owner_id": people["emmanuel"].id,
            "asset_ids": [asset["id"]],
            "initial_assessment": {
                "likelihood": 4,
                "impact": 5,
                "rationale": "Endpoint is public and unauthenticated.",
            },
        },
    ).json()
    assert risk["current"]["score"] == 20

    # 2. Assign a treatment action and upload supporting evidence.
    action = new_action(api, risk, people["emmanuel"].id, title="Verify HMAC webhook signatures")
    as_user(api, "emmanuel")
    upload = api.post(
        "/api/evidence",
        data={"target_type": "action", "target_id": action["id"], "description": "Design note"},
        files=pdf("design.pdf"),
    )
    assert upload.status_code == 201

    # 3. Complete the action without the risk score changing automatically.
    api.post(
        f"/api/actions/{action['id']}/complete",
        data={"note": "HMAC verification live; replayed forged webhooks rejected."},
        files=pdf("test-results.pdf"),
    )
    after_completion = api.get(f"/api/risks/{risk['id']}").json()
    assert after_completion["current"]["score"] == 20
    assert after_completion["status"] == "awaiting_reassessment"

    # 4. Perform and record a justified residual risk reassessment.
    as_user(api, "omotayo")
    residual = reassess(api, risk, 1, 5).json()
    assert (residual["original_score"], residual["score"]) == (20, 5)

    # 5. Submit a risk acceptance request and have a different authorised user approve it.
    as_user(api, "emmanuel")
    request = api.post(f"/api/risks/{risk['id']}/acceptances", json=acceptance_body()).json()
    own = api.post(
        f"/api/acceptances/{request['id']}/decision",
        json={"decision": "approve", "comment": "Approving my own request."},
    )
    assert own.status_code == 403
    as_user(api, "kelechi")
    approved = api.post(
        f"/api/acceptances/{request['id']}/decision",
        json={"decision": "approve", "comment": "Residual 5 is within appetite."},
    )
    assert approved.json()["status"] == "approved"

    # 7. An unauthorised user cannot approve or modify protected records.
    as_user(api, "ernestina")
    assert api.patch(f"/api/risks/{risk['id']}", json={"title": "Auditor edit"}).status_code == 403
    assert (
        api.post(
            f"/api/acceptances/{request['id']}/decision",
            json={"decision": "reject", "comment": "Auditor trying to reject."},
        ).status_code
        == 403
    )

    # Every step is in the audit chain, and the chain verifies.
    from app.services.audit import verify_chain

    actions = [e.action for e in db.exec(select(AuditLog).order_by(col(AuditLog.id)))]
    for expected in ("ASSESS", "UPLOAD", "COMPLETE", "REQUEST", "DENIED", "APPROVE"):
        assert expected in actions
    assert verify_chain(db).ok
