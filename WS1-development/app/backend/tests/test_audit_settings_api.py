"""P6 audit log API (T22 through HTTP), settings, CLI tools and security headers (T29)."""

from __future__ import annotations

import csv
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlmodel import Session, col, select
from typer.testing import CliRunner

from app.models import AuditLog, RiskAssessment
from tests.conftest import sign_in


def test_audit_log_listing_and_filters(seeded_api: TestClient) -> None:
    sign_in(seeded_api, "ernestina")
    page = seeded_api.get("/api/audit", params={"page_size": 5}).json()
    assert page["total"] > 100 and len(page["items"]) == 5
    assert page["items"][0]["id"] > page["items"][1]["id"]  # newest first
    approvals = seeded_api.get("/api/audit", params={"action": "APPROVE"}).json()
    assert {e["username"] for e in approvals["items"]} == {"kelechi", "adeola"}
    by_user = seeded_api.get("/api/audit", params={"username": "Gilbert"}).json()
    assert by_user["total"] > 0 and {e["username"] for e in by_user["items"]} == {"gilbert"}


@pytest.mark.parametrize("who", ["omotayo", "emmanuel"])
def test_audit_log_hidden_from_analysts_and_owners(seeded_api: TestClient, who: str) -> None:
    sign_in(seeded_api, who)
    assert seeded_api.get("/api/audit").status_code == 403
    assert seeded_api.get("/api/audit/verify").status_code == 403


def test_t22_verify_through_the_api_then_detect_tampering(
    seeded_api: TestClient, seeded: Session
) -> None:
    sign_in(seeded_api, "kelechi")
    ok = seeded_api.get("/api/audit/verify").json()
    assert ok["ok"] is True and ok["entries_checked"] > 100 and len(ok["head_hash"]) == 64

    # A database owner edits an approval entry (bypassing the insert-only trigger).
    victim = seeded.exec(select(AuditLog).where(AuditLog.action == "APPROVE")).first()
    assert victim is not None
    if seeded.get_bind().dialect.name == "postgresql":
        seeded.exec(text("ALTER TABLE audit_log DISABLE TRIGGER trg_audit_log_insert_only"))  # type: ignore[call-overload]
    else:
        seeded.exec(text("DROP TRIGGER trg_audit_log_no_update"))  # type: ignore[call-overload]
    victim.detail = "R-014: nothing to see here"
    seeded.add(victim)
    seeded.commit()

    broken = seeded_api.get("/api/audit/verify").json()
    assert broken["ok"] is False and broken["first_broken_id"] == victim.id
    assert broken["problem"] == "entry content does not match its hash"


def test_audit_csv_export_in_utc(seeded_api: TestClient, seeded: Session) -> None:
    sign_in(seeded_api, "ernestina")
    response = seeded_api.get("/api/audit.csv", params={"action": "COMPLETE"})
    rows = list(csv.DictReader(response.content.decode("utf-8-sig").splitlines()))
    assert len(rows) == 2 and all(r["occurred_at_utc"].endswith("Z") for r in rows)
    assert json.loads(rows[0]["after"])["status"] == "completed"
    last = seeded.exec(select(AuditLog).order_by(col(AuditLog.id).desc())).first()
    assert last is not None and (last.action, last.object_type) == ("EXPORT", "audit_log")


# ── Settings ───────────────────────────────────────────────────────────────────────────────


def test_settings_readable_by_all_changed_by_admin_and_audited(
    seeded_api: TestClient, seeded: Session
) -> None:
    sign_in(seeded_api, "emmanuel")
    assert seeded_api.get("/api/settings").json()["appetite_threshold"] == 10
    assert seeded_api.patch("/api/settings", json={"appetite_threshold": 12}).status_code == 403
    seeded_api.cookies.clear()
    sign_in(seeded_api, "admin")
    changed = seeded_api.patch(
        "/api/settings", json={"appetite_threshold": 12, "sla_days_critical": 21}
    )
    assert changed.status_code == 200
    body = changed.json()
    assert (body["appetite_threshold"], body["sla_days_critical"]) == (12, 21)
    assert body["updated_by"] == "System Administrator"
    entry = seeded.exec(select(AuditLog).where(AuditLog.action == "SETTING")).one()
    assert entry.before == {"appetite_threshold": 10, "sla_days_critical": 30}


def test_threshold_change_applies_to_new_assessments_only(
    seeded_api: TestClient, seeded: Session
) -> None:
    sign_in(seeded_api, "admin")
    seeded_api.patch("/api/settings", json={"appetite_threshold": 13})
    stored = seeded.exec(select(RiskAssessment).where(RiskAssessment.score == 12)).first()
    assert stored is not None and stored.above_appetite is True and stored.appetite_threshold == 10
    seeded_api.cookies.clear()
    sign_in(seeded_api, "omotayo")
    risks = seeded_api.get("/api/risks", params={"page_size": 100}).json()["items"]
    r1 = next(r for r in risks if r["risk_code"] == "R-001")
    assert r1["current"]["explanation"].endswith(
        "Above appetite (threshold 10). Remediation due within 30 days."
    )


@pytest.mark.parametrize(
    "body",
    [
        {"appetite_threshold": 0},
        {"appetite_threshold": 26},
        {"org_timezone": "system"},
        {"org_timezone": "Mars/Base"},
        {"sla_days_high": 0},
    ],
)
def test_invalid_settings_rejected(seeded_api: TestClient, body: dict) -> None:
    sign_in(seeded_api, "admin")
    assert seeded_api.patch("/api/settings", json=body).status_code == 422


# ── CLI tools ──────────────────────────────────────────────────────────────────────────────


def test_verify_audit_cli_on_test_database(migrated_engine) -> None:  # type: ignore[no-untyped-def]
    from app.cli import cli

    result = CliRunner().invoke(cli, ["verify-audit"])
    assert result.exit_code in (0, 1) and ("OK:" in result.output or "BROKEN" in result.output)


def test_export_backup(seeded: Session, tmp_path) -> None:  # type: ignore[no-untyped-def]
    from app.services.backup import export_all

    path, counts = export_all(seeded, tmp_path, with_evidence=False)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert counts["risk"] >= 22 and counts["audit_log"] > 100
    assert "content" not in payload["tables"]["evidence"][0]
    path2, _ = export_all(seeded, tmp_path / "full", with_evidence=True)
    evidence = json.loads(path2.read_text(encoding="utf-8"))["tables"]["evidence"][0]
    assert set(evidence["content"]) == {"base64"}


# ── Security headers (T29) ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "path",
    [
        "/api/health",
        "/api/me",
        "/api/risks",
        "/api/dashboard",
        "/api/reports/management.csv",
        "/api/nope",
    ],
)
def test_t29_security_headers_on_every_kind_of_response(seeded_api: TestClient, path: str) -> None:
    sign_in(seeded_api, "omotayo")
    response = seeded_api.get(path)
    headers = response.headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in headers["content-security-policy"]
    assert headers["strict-transport-security"].startswith("max-age=31536000")
    assert headers["permissions-policy"].startswith("geolocation=()")
    assert headers["referrer-policy"] == "same-origin"
