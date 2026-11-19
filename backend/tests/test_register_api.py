"""P4 register API: services, assets, risks, initial assessment, filters, permissions.

Covers T01 (L4 x I5 = 20 through the API), T02 (out-of-range rejected), T05 (risk needs an
asset), T11 (assessments can't be edited or deleted), T19/T21 (refusals and ownership).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, col, select

from app.models import AuditLog, RiskAssessment
from tests.conftest import sign_in


@pytest.fixture
def register(api: TestClient, people: dict, db: Session) -> dict:
    """Two services, three assets, signed in as the analyst."""
    sign_in(api, "omotayo")
    s1 = api.post(
        "/api/services",
        json={
            "code": "S1",
            "name": "Savings and Wallets",
            "owner_id": people["emmanuel"].id,
            "criticality": 5,
        },
    ).json()
    s2 = api.post("/api/services", json={"code": "S2", "name": "Investments"}).json()
    ledger = api.post(
        "/api/assets",
        json={
            "name": "Wallet ledger",
            "asset_type": "database",
            "service_id": s1["id"],
            "classification": "restricted",
        },
    ).json()
    gateway = api.post(
        "/api/assets",
        json={"name": "Payment gateway integration", "asset_type": "api", "service_id": s1["id"]},
    ).json()
    fund_api = api.post(
        "/api/assets",
        json={
            "name": "Fund manager API",
            "asset_type": "third_party_service",
            "service_id": s2["id"],
        },
    ).json()
    return {"s1": s1, "s2": s2, "ledger": ledger, "gateway": gateway, "fund_api": fund_api}


def risk_body(owner_id: int, asset_ids: list[int], **extra: object) -> dict:
    body = {
        "title": "Double-spend through a ledger race condition",
        "description": "Concurrent requests can debit twice.",
        "threat": "Bots sending concurrent withdrawals",
        "vulnerability": "No row locking or idempotency keys",
        "business_impact": "Direct loss of customer funds",
        "category": "integrity",
        "owner_id": owner_id,
        "asset_ids": asset_ids,
    }
    body.update(extra)
    return body


L4_I5 = {
    "likelihood": 4,
    "impact": 5,
    "rationale": "Reproduced in load testing; endpoints exposed to the mobile app.",
}


# ── Services and assets ────────────────────────────────────────────────────────────────────


def test_assets_get_sequential_codes_and_service_details(register: dict) -> None:
    assert [register[k]["asset_code"] for k in ("ledger", "gateway", "fund_api")] == [
        "A-001",
        "A-002",
        "A-003",
    ]
    assert register["ledger"]["service"]["code"] == "S1"
    assert register["ledger"]["classification"] == "restricted"


def test_asset_name_unique_per_service(api: TestClient, register: dict) -> None:
    again = {"name": "wallet LEDGER", "asset_type": "database", "service_id": register["s1"]["id"]}
    assert api.post("/api/assets", json=again).status_code == 409
    elsewhere = {**again, "service_id": register["s2"]["id"]}
    assert api.post("/api/assets", json=elsewhere).status_code == 201


def test_asset_with_obligations_and_unknown_ids(
    api: TestClient, register: dict, db: Session
) -> None:
    from app.services.reference_data import load_reference_data

    load_reference_data(db)
    obligations = api.get("/api/obligations", params={"regime": "PCI-DSS-4.0"}).json()
    body = {
        "name": "Card vault",
        "asset_type": "data_store",
        "service_id": register["s1"]["id"],
        "obligation_ids": [o["id"] for o in obligations[:2]],
    }
    created = api.post("/api/assets", json=body).json()
    assert [o["regime"] for o in created["obligations"]] == ["PCI-DSS-4.0", "PCI-DSS-4.0"]
    bad = api.post("/api/assets", json={**body, "name": "Other", "obligation_ids": [99999]})
    assert bad.status_code == 422 and "Unknown obligation id" in bad.json()["detail"]


def test_services_list_counts(api: TestClient, register: dict) -> None:
    api.post(
        "/api/risks",
        json=risk_body(
            register["s1"]["owner"]["id"], [register["ledger"]["id"], register["gateway"]["id"]]
        ),
    )
    s1 = next(s for s in api.get("/api/services").json() if s["code"] == "S1")
    assert (s1["asset_count"], s1["risk_count"]) == (2, 1)
    assert s1["owner"]["full_name"] == "Emmanuel Teye Adjei"


@pytest.mark.parametrize("who", ["emmanuel", "kelechi", "ernestina"])
def test_t19_only_analysts_and_admins_change_the_register(
    api: TestClient, register: dict, who: str
) -> None:
    api.cookies.clear()
    sign_in(api, who)
    body = {
        "name": "Shadow IT laptop",
        "asset_type": "endpoint",
        "service_id": register["s1"]["id"],
    }
    assert api.post("/api/assets", json=body).status_code == 403
    assert (
        api.patch(f"/api/assets/{register['ledger']['id']}", json={"name": "x" * 5}).status_code
        == 403
    )
    assert api.get("/api/assets").status_code == 200  # reading is fine


def test_asset_update_audited(api: TestClient, register: dict, db: Session) -> None:
    asset_id = register["ledger"]["id"]
    response = api.patch(f"/api/assets/{asset_id}", json={"classification": "confidential"})
    assert response.status_code == 200 and response.json()["classification"] == "confidential"
    entry = db.exec(select(AuditLog).order_by(col(AuditLog.id).desc())).first()
    assert entry is not None and entry.action == "UPDATE" and entry.object_type == "asset"
    assert entry.before["classification"] == "restricted"  # type: ignore[index]


# ── Risks and the initial assessment ───────────────────────────────────────────────────────


def test_t01_create_risk_with_l4_i5_scores_20_with_explanation(
    api: TestClient, register: dict, people: dict
) -> None:
    body = risk_body(people["emmanuel"].id, [register["ledger"]["id"]], initial_assessment=L4_I5)
    response = api.post("/api/risks", json=body)
    assert response.status_code == 201, response.text
    risk = response.json()
    assert risk["risk_code"] == "R-001" and risk["status"] == "open"
    current = risk["current"]
    assert (current["score"], current["band"], current["above_appetite"]) == (20, "critical", True)
    assert current["explanation"] == (
        "Likelihood 4 (Likely) × Impact 5 (Severe) = 20 → Critical. "
        "Above appetite (threshold 10). Remediation due within 30 days."
    )
    assert risk["original_score"] == 20
    assert (
        len(risk["assessments"]) == 1
        and risk["assessments"][0]["assessed_by"]["full_name"] == "Omotayo Akinola"
    )
    assert risk["next_review_date"] is not None  # set from the critical review cycle
    assert risk["services"] == ["S1"]


@pytest.mark.parametrize(
    ("likelihood", "impact"), [(0, 3), (6, 3), (3, 0), (3, 6), ("4", 5), (4.0, 5)]
)
def test_t02_out_of_range_or_non_integer_values_rejected(
    api: TestClient, register: dict, people: dict, likelihood: object, impact: object
) -> None:
    body = risk_body(
        people["emmanuel"].id,
        [register["ledger"]["id"]],
        initial_assessment={**L4_I5, "likelihood": likelihood, "impact": impact},
    )
    response = api.post("/api/risks", json=body)
    assert response.status_code == 422
    assert api.get("/api/risks").json()["total"] == 0  # nothing half-created


def test_t05_risk_without_assets_rejected(api: TestClient, register: dict, people: dict) -> None:
    assert api.post("/api/risks", json=risk_body(people["emmanuel"].id, [])).status_code == 422
    unknown = api.post("/api/risks", json=risk_body(people["emmanuel"].id, [424242]))
    assert unknown.status_code == 422 and "Unknown asset id" in unknown.json()["detail"]


def test_risk_owner_must_be_owner_or_approver(
    api: TestClient, register: dict, people: dict
) -> None:
    for who in ("omotayo", "ernestina", "admin"):
        response = api.post(
            "/api/risks", json=risk_body(people[who].id, [register["ledger"]["id"]])
        )
        assert response.status_code == 422 and "owner or approver role" in response.json()["detail"]
    ciso = api.post("/api/risks", json=risk_body(people["adeola"].id, [register["ledger"]["id"]]))
    assert ciso.status_code == 201  # the CISO may own a risk (R-015 in the demo)


def test_initial_assessment_separately_then_only_once(
    api: TestClient, register: dict, people: dict, db: Session
) -> None:
    risk = api.post(
        "/api/risks", json=risk_body(people["anita"].id, [register["fund_api"]["id"]])
    ).json()
    assert risk["current"] is None and risk["next_review_date"] is None
    scored = api.post(
        f"/api/risks/{risk['id']}/assessments",
        json={"likelihood": 3, "impact": 3, "rationale": "Two outages this year."},
    )
    assert scored.status_code == 201
    assert (
        scored.json()["current"]["score"] == 9
        and scored.json()["current"]["above_appetite"] is False
    )
    again = api.post(f"/api/risks/{risk['id']}/assessments", json=L4_I5)
    assert (
        again.status_code == 409 and "already has its initial assessment" in again.json()["detail"]
    )
    assessment = db.exec(select(AuditLog).where(AuditLog.action == "ASSESS")).first()
    assert assessment is not None and "= 9 → Medium" in (assessment.detail or "")


def test_rationale_too_short_rejected(api: TestClient, register: dict, people: dict) -> None:
    body = risk_body(
        people["emmanuel"].id,
        [register["ledger"]["id"]],
        initial_assessment={**L4_I5, "rationale": "because"},
    )
    assert api.post("/api/risks", json=body).status_code == 422


def test_t11_no_route_edits_or_deletes_an_assessment(
    api: TestClient, register: dict, people: dict, db: Session
) -> None:
    risk = api.post(
        "/api/risks",
        json=risk_body(people["emmanuel"].id, [register["ledger"]["id"]], initial_assessment=L4_I5),
    ).json()
    assessment_id = risk["assessments"][0]["id"]
    base = f"/api/risks/{risk['id']}/assessments"
    assert api.put(f"{base}/{assessment_id}", json=L4_I5).status_code in (404, 405)
    assert api.patch(f"{base}/{assessment_id}", json=L4_I5).status_code in (404, 405)
    assert api.delete(f"{base}/{assessment_id}").status_code in (404, 405)
    assert api.delete(base).status_code == 405
    assert db.get(RiskAssessment, assessment_id).score == 20  # type: ignore[union-attr]


def test_owners_and_auditors_cannot_create_or_assess(
    api: TestClient, register: dict, people: dict
) -> None:
    risk = api.post(
        "/api/risks", json=risk_body(people["emmanuel"].id, [register["ledger"]["id"]])
    ).json()
    for who in ("emmanuel", "ernestina", "kelechi"):
        api.cookies.clear()
        sign_in(api, who)
        body = risk_body(people["emmanuel"].id, [register["ledger"]["id"]])
        assert api.post("/api/risks", json=body).status_code == 403
        assert api.post(f"/api/risks/{risk['id']}/assessments", json=L4_I5).status_code == 403


# ── Editing risks: analyst vs owner (T21) ──────────────────────────────────────────────────


def test_analyst_edits_any_field_and_links(
    api: TestClient, register: dict, people: dict, db: Session
) -> None:
    risk = api.post(
        "/api/risks", json=risk_body(people["emmanuel"].id, [register["ledger"]["id"]])
    ).json()
    response = api.patch(
        f"/api/risks/{risk['id']}",
        json={
            "title": "Ledger race condition (confirmed)",
            "owner_id": people["anita"].id,
            "asset_ids": [register["ledger"]["id"], register["gateway"]["id"]],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["owner"]["full_name"] == "Anita Ojimba"
    assert [a["asset_code"] for a in body["assets"]] == ["A-001", "A-002"]
    entry = db.exec(select(AuditLog).order_by(col(AuditLog.id).desc())).first()
    assert entry is not None and set(entry.after) == {"title", "owner_id", "asset_ids"}  # type: ignore[arg-type]


def test_analyst_cannot_remove_every_asset(api: TestClient, register: dict, people: dict) -> None:
    risk = api.post(
        "/api/risks", json=risk_body(people["emmanuel"].id, [register["ledger"]["id"]])
    ).json()
    assert api.patch(f"/api/risks/{risk['id']}", json={"asset_ids": []}).status_code == 422


def test_owner_may_edit_description_and_review_date_of_own_risk_only(
    api: TestClient, register: dict, people: dict, db: Session
) -> None:
    mine = api.post(
        "/api/risks", json=risk_body(people["emmanuel"].id, [register["ledger"]["id"]])
    ).json()
    theirs = api.post(
        "/api/risks", json=risk_body(people["anita"].id, [register["fund_api"]["id"]])
    ).json()
    api.cookies.clear()
    sign_in(api, "emmanuel")

    ok = api.patch(
        f"/api/risks/{mine['id']}",
        json={"description": "Load test reproduced it.", "next_review_date": "2027-01-15"},
    )
    assert ok.status_code == 200 and ok.json()["next_review_date"] == "2027-01-15"

    restricted = api.patch(f"/api/risks/{mine['id']}", json={"title": "Downplayed title"})
    assert restricted.status_code == 403 and "not: title" in restricted.json()["detail"]

    other = api.patch(f"/api/risks/{theirs['id']}", json={"description": "Not my risk"})
    assert other.status_code == 403  # T21: another owner's record
    denied = db.exec(
        select(AuditLog).where(AuditLog.action == "DENIED").order_by(col(AuditLog.id).desc())
    ).first()
    assert (
        denied is not None
        and denied.object_id == str(theirs["id"])
        and denied.username == "emmanuel"
    )


def test_unknown_risk_is_404(api: TestClient, register: dict) -> None:
    assert api.get("/api/risks/987654").status_code == 404
    assert api.patch("/api/risks/987654", json={"description": "x"}).status_code == 404


# ── Listing and filters ────────────────────────────────────────────────────────────────────


def test_list_filters_sort_and_pagination(api: TestClient, register: dict, people: dict) -> None:
    def make(
        owner: str, asset: str, title: str, likelihood: int | None, impact: int | None
    ) -> None:
        body = risk_body(people[owner].id, [register[asset]["id"]], title=title)
        if likelihood:
            body["initial_assessment"] = {
                "likelihood": likelihood,
                "impact": impact,
                "rationale": "Scored for the filter test.",
            }
        assert api.post("/api/risks", json=body).status_code == 201

    make("emmanuel", "ledger", "Ledger double spend", 4, 5)  # 20 critical
    make("emmanuel", "gateway", "Webhook spoofing", 3, 4)  # 12 high
    make("anita", "fund_api", "Fund API outage", 3, 3)  # 9 medium
    make("anita", "fund_api", "Unscored placeholder risk", None, None)

    def codes(**params: object) -> list[str]:
        return [r["title"] for r in api.get("/api/risks", params=params).json()["items"]]

    assert codes() == [
        "Ledger double spend",
        "Webhook spoofing",
        "Fund API outage",
        "Unscored placeholder risk",
    ]  # highest score first
    assert codes(above_appetite=True) == ["Ledger double spend", "Webhook spoofing"]
    assert codes(above_appetite=False) == ["Fund API outage"]
    assert codes(band="high") == ["Webhook spoofing"]
    assert codes(service_id=register["s2"]["id"]) == [
        "Fund API outage",
        "Unscored placeholder risk",
    ]
    assert codes(owner_id=people["emmanuel"].id) == ["Ledger double spend", "Webhook spoofing"]
    assert codes(unassessed=True) == ["Unscored placeholder risk"]
    assert codes(q="WEBHOOK") == ["Webhook spoofing"]
    assert codes(sort="code")[0] == "Ledger double spend"

    page2 = api.get("/api/risks", params={"page": 2, "page_size": 3}).json()
    assert page2["total"] == 4 and [r["title"] for r in page2["items"]] == [
        "Unscored placeholder risk"
    ]
    assert api.get("/api/risks", params={"page_size": 500}).status_code == 422
    assert api.get("/api/risks", params={"sort": "drop table"}).status_code == 422


def test_reading_the_register_needs_sign_in(api: TestClient) -> None:
    for path in ("/api/risks", "/api/assets", "/api/services", "/api/obligations", "/api/controls"):
        assert api.get(path).status_code == 401


# ── Remaining register routes ──────────────────────────────────────────────────────────────


def test_service_update_rules(api: TestClient, register: dict, people: dict, db: Session) -> None:
    s1 = register["s1"]["id"]
    ok = api.patch(f"/api/services/{s1}", json={"criticality": 4, "owner_id": people["anita"].id})
    assert ok.status_code == 200 and ok.json()["owner"]["full_name"] == "Anita Ojimba"
    assert api.patch(f"/api/services/{s1}", json={"name": "investments"}).status_code == 409
    assert api.patch(f"/api/services/{s1}", json={"owner_id": 999999}).status_code == 422
    assert api.patch("/api/services/999999", json={"criticality": 2}).status_code == 404
    duplicate = {"code": "S1", "name": "Another service"}
    assert api.post("/api/services", json=duplicate).status_code == 409
    entry = db.exec(
        select(AuditLog).where(AuditLog.object_type == "service", AuditLog.action == "UPDATE")
    ).first()
    assert entry is not None and entry.before["criticality"] == 5  # type: ignore[index]


def test_obligations_and_controls_catalogue(api: TestClient, register: dict, db: Session) -> None:
    from app.services.reference_data import load_reference_data

    load_reference_data(db)
    body = {"regime": "NDPA-2023", "reference": "NDPA-99", "short_title": "Appoint a DPO"}
    created = api.post("/api/obligations", json=body)
    assert created.status_code == 201 and created.json()["reference"] == "NDPA-99"
    assert api.post("/api/obligations", json=body).status_code == 409
    ndpa = api.get("/api/obligations", params={"regime": "NDPA-2023"}).json()
    assert all(o["regime"] == "NDPA-2023" for o in ndpa) and len(ndpa) >= 6
    csf = api.get("/api/controls", params={"framework": "NIST-CSF-2.0"}).json()
    assert {c["control_ref"] for c in csf} >= {"ID.RA", "PR.AA", "GV.RM"}
    assert len(api.get("/api/controls").json()) > len(csf)


def test_asset_detail_and_obligation_relinking(
    api: TestClient, register: dict, db: Session
) -> None:
    from app.services.reference_data import load_reference_data

    load_reference_data(db)
    pci = [o["id"] for o in api.get("/api/obligations", params={"regime": "PCI-DSS-4.0"}).json()]
    asset_id = register["gateway"]["id"]
    linked = api.patch(f"/api/assets/{asset_id}", json={"obligation_ids": pci[:3]})
    assert linked.status_code == 200 and len(linked.json()["obligations"]) == 3
    relinked = api.patch(f"/api/assets/{asset_id}", json={"obligation_ids": pci[:1]}).json()
    assert len(relinked["obligations"]) == 1
    detail = api.get(f"/api/assets/{asset_id}").json()
    assert detail["name"] == "Payment gateway integration" and detail["risk_count"] == 0
    assert api.get("/api/assets/999999").status_code == 404
    assert api.patch("/api/assets/999999", json={"status": "retired"}).status_code == 404
    clash = api.patch(f"/api/assets/{asset_id}", json={"name": "Wallet ledger"})
    assert clash.status_code == 409
    assert api.patch(f"/api/assets/{asset_id}", json={"owner_id": 999999}).status_code == 422
    unknown = api.patch(f"/api/assets/{asset_id}", json={"obligation_ids": [999999]})
    assert unknown.status_code == 422


def test_asset_list_search_and_service_filter(api: TestClient, register: dict) -> None:
    by_service = api.get("/api/assets", params={"service_id": register["s2"]["id"]}).json()
    assert [a["name"] for a in by_service] == ["Fund manager API"]
    assert [a["asset_code"] for a in api.get("/api/assets", params={"q": "GATEWAY"}).json()] == [
        "A-002"
    ]


def test_asset_highest_score_follows_current_assessment(
    api: TestClient, register: dict, people: dict
) -> None:
    for likelihood, impact in ((2, 2), (4, 5)):
        body = risk_body(
            people["emmanuel"].id,
            [register["ledger"]["id"]],
            title=f"Ledger risk scored {likelihood * impact}",
            initial_assessment={
                "likelihood": likelihood,
                "impact": impact,
                "rationale": "Scored for the asset view test.",
            },
        )
        api.post("/api/risks", json=body)
    ledger = api.get(f"/api/assets/{register['ledger']['id']}").json()
    assert (ledger["risk_count"], ledger["highest_score"]) == (2, 20)


def test_risk_detail_lists_obligations(
    api: TestClient, register: dict, people: dict, db: Session
) -> None:
    from app.services.reference_data import load_reference_data

    load_reference_data(db)
    ids = [o["id"] for o in api.get("/api/obligations", params={"regime": "CBN"}).json()[:2]]
    risk = api.post(
        "/api/risks",
        json=risk_body(people["emmanuel"].id, [register["ledger"]["id"]], obligation_ids=ids),
    ).json()
    assert [o["reference"] for o in risk["obligations"]] == ["CBN-01", "CBN-02"]
    filtered = api.get("/api/risks", params={"obligation_id": ids[0]}).json()
    assert filtered["total"] == 1
