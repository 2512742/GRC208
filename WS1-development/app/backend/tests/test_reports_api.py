"""P6 dashboard and management report on the seeded Alajo data (T17, T18).

Every figure is cross-checked against an independent query on the database, so the dashboard
can't drift from the data it summarises.
"""

from __future__ import annotations

import csv
import io
from collections import Counter

from fastapi.testclient import TestClient
from sqlmodel import Session, col, func, select

from app.models import AcceptanceRequest, AuditLog, Risk, RiskAssessment, TreatmentAction
from app.services.governance import org_today
from app.services.workflow import acceptance_is_expired, action_is_overdue
from tests.conftest import sign_in


def latest_scores(db: Session) -> dict[int, RiskAssessment]:
    latest: dict[int, RiskAssessment] = {}
    for row in db.exec(select(RiskAssessment).order_by(col(RiskAssessment.id))):
        latest[row.risk_id] = row
    return latest


def test_t17_dashboard_matches_the_database(seeded_api: TestClient, seeded: Session) -> None:
    sign_in(seeded_api, "ernestina")  # even the read-only auditor sees the dashboard
    data = seeded_api.get("/api/dashboard").json()
    db = seeded
    latest = latest_scores(db)
    today = org_today(db)

    # Heat map counts per (likelihood, impact) equal a direct count of current assessments.
    expected = Counter((a.likelihood, a.impact) for a in latest.values())
    shown = {(c["likelihood"], c["impact"]): c["count"] for c in data["heat_map_current"]}
    assert len(shown) == 25 and shown == {k: expected.get(k, 0) for k in shown}

    originals = Counter(
        (a.likelihood, a.impact)
        for a in db.exec(select(RiskAssessment).where(RiskAssessment.assessment_type == "initial"))
    )
    shown_original = {(c["likelihood"], c["impact"]): c["count"] for c in data["heat_map_original"]}
    assert shown_original == {k: originals.get(k, 0) for k in shown_original}

    above = {r.risk_code for r in db.exec(select(Risk)) if latest[r.id].above_appetite}
    assert {r["risk_code"] for r in data["above_appetite"]} == above
    assert data["totals"]["above_appetite"] == len(above) == 14

    overdue = [
        a.action_code
        for a in db.exec(select(TreatmentAction))
        if action_is_overdue(a.status, a.due_date, today)
    ]
    assert [o["action_code"] for o in data["overdue_actions"]] == overdue == ["T-003"]
    expired = [
        a
        for a in db.exec(select(AcceptanceRequest))
        if acceptance_is_expired(a.status, a.expiry_date, today)
    ]
    assert data["totals"]["expired_acceptances"] == len(expired) == 1
    assert data["totals"]["pending_acceptances"] == 2
    assert data["totals"]["awaiting_reassessment"] == 1
    assert sum(data["by_band"].values()) == data["totals"]["assessed"] == 22
    assert data["upcoming_reviews"] and all(r["review_due_soon"] for r in data["upcoming_reviews"])
    assert data["risks"] == []  # the dashboard carries aggregates only
    assert {s["code"] for s in data["by_service"]} == {"S1", "S2", "S3"}
    assert {e["regime"] for e in data["regulatory_exposure"]} == {
        "CBN",
        "NDPA-2023",
        "PCI-DSS-4.0",
        "SEC-NG",
    }


def test_original_vs_current_heat_map_differs_after_reassessment(seeded_api: TestClient) -> None:
    sign_in(seeded_api, "omotayo")
    data = seeded_api.get("/api/dashboard").json()
    current = {(c["likelihood"], c["impact"]): c["risk_codes"] for c in data["heat_map_current"]}
    original = {(c["likelihood"], c["impact"]): c["risk_codes"] for c in data["heat_map_original"]}
    assert "R-013" in current[(1, 4)] and "R-013" in original[(3, 4)]


def test_dashboard_filters(seeded_api: TestClient) -> None:
    sign_in(seeded_api, "omotayo")
    s2 = seeded_api.get("/api/services").json()[1]
    data = seeded_api.get("/api/dashboard", params={"service_id": s2["id"]}).json()
    assert data["totals"]["risks"] == s2["risk_count"]
    critical = seeded_api.get("/api/dashboard", params={"band": "critical"}).json()
    assert critical["by_band"] == {"low": 0, "medium": 0, "high": 0, "critical": 8}


def test_dashboard_needs_sign_in(seeded_api: TestClient) -> None:
    assert seeded_api.get("/api/dashboard").status_code == 401


def test_t18_management_report_json_matches_filters(seeded_api: TestClient) -> None:
    sign_in(seeded_api, "kelechi")
    report = seeded_api.get("/api/reports/management", params={"above_appetite": True}).json()
    assert len(report["risks"]) == 14
    assert all(r["current"]["above_appetite"] for r in report["risks"])


def test_t18_csv_export_filtered_stamped_and_audited(
    seeded_api: TestClient, seeded: Session
) -> None:
    sign_in(seeded_api, "kelechi")
    response = seeded_api.get(
        "/api/reports/management.csv", params={"band": "critical", "tz": "Africa/Kampala"}
    )
    assert response.status_code == 200
    assert response.headers["content-disposition"].startswith('attachment; filename="alajo-')
    text = response.content.decode("utf-8-sig")
    comments = [line for line in text.splitlines() if line.startswith("#")]
    assert "Generated by Kelechi Kenneth Nwankwo (approver)" in comments[0]
    assert "EAT" in comments[0] and "Z)" in comments[0]
    assert "Deadlines and expiry evaluated in Africa/Lagos (WAT)" in comments[1]
    assert "band=critical" in comments[2]
    rows = list(csv.DictReader(line for line in text.splitlines() if not line.startswith("#")))
    assert len(rows) == 8 and {r["band"] for r in rows} == {"critical"}
    assert all(r["generated_at_utc"].endswith("Z") for r in rows)
    entry = seeded.exec(select(AuditLog).order_by(col(AuditLog.id).desc())).first()
    assert entry is not None and (entry.action, entry.object_id) == ("EXPORT", "csv")
    assert "band=critical" in (entry.detail or "")


def test_csv_inherent_and_residual_columns(seeded_api: TestClient) -> None:
    sign_in(seeded_api, "kelechi")
    text = seeded_api.get("/api/reports/management.csv").content.decode("utf-8-sig")
    rows = list(csv.DictReader(line for line in text.splitlines() if not line.startswith("#")))
    assert all(r["inherent_score"] for r in rows)
    reassessed = [r for r in rows if r["residual_score"]]
    assert reassessed, "the demo data has reassessed risks"
    for r in reassessed:
        assert r["residual_score"] == r["score"]
        assert int(r["reduction"]) == int(r["inherent_score"]) - int(r["residual_score"])
    assert all(r["reduction"] == "" for r in rows if not r["residual_score"])


def test_t18_pdf_export(seeded_api: TestClient) -> None:
    sign_in(seeded_api, "ernestina")
    response = seeded_api.get("/api/reports/management.pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-") and len(response.content) > 3000


def test_csv_neutralises_spreadsheet_formulas(seeded_api: TestClient, seeded: Session) -> None:
    risk = seeded.exec(select(Risk).where(Risk.risk_code == "R-022")).one()
    risk.title = '=HYPERLINK("http://evil.example","click")'
    seeded.add(risk)
    seeded.commit()
    sign_in(seeded_api, "omotayo")
    text = seeded_api.get("/api/reports/management.csv").content.decode("utf-8-sig")
    rows = list(
        csv.reader(
            io.StringIO("\n".join(line for line in text.splitlines() if not line.startswith("#")))
        )
    )
    titles = [r[1] for r in rows[1:]]
    assert '\'=HYPERLINK("http://evil.example","click")' in titles


def test_report_needs_sign_in(seeded_api: TestClient) -> None:
    for path in (
        "/api/reports/management",
        "/api/reports/management.csv",
        "/api/reports/management.pdf",
    ):
        assert seeded_api.get(path).status_code == 401


def test_report_counts_agree_with_dashboard(seeded_api: TestClient, seeded: Session) -> None:
    sign_in(seeded_api, "omotayo")
    report = seeded_api.get("/api/reports/management").json()
    dash = seeded_api.get("/api/dashboard").json()
    assert report["totals"] == dash["totals"]
    total_risks = seeded.exec(select(func.count()).select_from(Risk)).one()
    assert len(report["risks"]) == total_risks
