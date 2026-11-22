"""P6 CSV import on the seeded Alajo data (T24 valid import, T25 rejected rows explained,
T26 the same file twice creates nothing twice)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, func, select

from app.models import Asset, AuditLog, Evidence, Risk
from app.services.demo_seed import SAMPLE_DIR
from tests.conftest import sign_in


def upload(api: TestClient, kind: str, name: str, content: bytes):  # type: ignore[no-untyped-def]
    return api.post(f"/api/imports/{kind}", files={"file": (name, content, "text/csv")})


def sample(name: str) -> bytes:
    return (SAMPLE_DIR / name).read_bytes()


def count(db: Session, model: type) -> int:
    return db.exec(select(func.count()).select_from(model)).one()


def test_templates_downloadable(seeded_api: TestClient) -> None:
    sign_in(seeded_api, "omotayo")
    for kind, first in (("assets", "asset_code,name"), ("risks", "risk_code,title")):
        response = seeded_api.get(f"/api/imports/templates/{kind}.csv")
        assert response.status_code == 200
        assert response.content.decode("utf-8-sig").startswith(first)


def test_t24_valid_assets_file_previewed_then_committed(
    seeded_api: TestClient, seeded: Session
) -> None:
    sign_in(seeded_api, "omotayo")
    before = count(seeded, Asset)
    preview = upload(
        seeded_api, "assets", "assets_import_valid.csv", sample("assets_import_valid.csv")
    )
    assert preview.status_code == 201, preview.text
    batch = preview.json()
    assert (batch["status"], batch["total_rows"], batch["valid_rows"]) == ("previewed", 3, 3)
    assert count(seeded, Asset) == before  # nothing created by a preview
    stored = seeded.get(Evidence, batch["evidence_id"])
    assert stored is not None and stored.target_type == "import_batch"  # file kept as evidence

    committed = seeded_api.post(f"/api/imports/{batch['id']}/commit").json()
    assert committed["status"] == "committed"
    assert [r["created"] for r in committed["rows"]] == ["A-019", "A-020", "A-021"]
    assert count(seeded, Asset) == before + 3
    imports = seeded.exec(select(AuditLog).where(AuditLog.action == "IMPORT")).all()
    assert [e.after["status"] for e in imports][-2:] == ["previewed", "committed"]  # type: ignore[index]


def test_t25_errors_file_explains_every_rejected_row(
    seeded_api: TestClient, seeded: Session
) -> None:
    sign_in(seeded_api, "omotayo")
    batch = upload(
        seeded_api,
        "assets",
        "assets_import_with_errors.csv",
        sample("assets_import_with_errors.csv"),
    ).json()
    assert (
        batch["total_rows"],
        batch["valid_rows"],
        batch["rejected_rows"],
        batch["duplicate_rows"],
    ) == (9, 1, 5, 3)
    reasons = {r["row"]: (r["status"], " ".join(r["reasons"])) for r in batch["rows"]}
    assert reasons[2] == ("valid", "")
    assert reasons[3][0] == "rejected" and "asset_type" in reasons[3][1]
    assert reasons[4] == ("rejected", "name: is required")
    assert reasons[5] == ("rejected", "service_code: no business service 'S9'")
    assert reasons[6] == ("duplicate", "an asset named 'Wallet ledger' already exists in S1")
    assert reasons[7] == ("duplicate", "repeats an earlier row in this file")
    assert reasons[8] == ("rejected", "owner_username: no active user 'nobody'")
    assert reasons[9] == ("rejected", "obligations: unknown reference(s) NDPA-99")
    assert reasons[10] == ("duplicate", "asset_code A-007 already exists")
    before = count(seeded, Asset)
    committed = seeded_api.post(f"/api/imports/{batch['id']}/commit").json()
    assert count(seeded, Asset) == before + 1  # only the valid row
    assert [r["created"] for r in committed["rows"] if r.get("created")] == ["A-019"]


def test_t26_same_file_twice_creates_nothing_twice(seeded_api: TestClient, seeded: Session) -> None:
    sign_in(seeded_api, "omotayo")
    content = sample("assets_import_valid.csv")
    first = upload(seeded_api, "assets", "valid.csv", content).json()
    seeded_api.post(f"/api/imports/{first['id']}/commit")
    after_first = count(seeded, Asset)
    second = upload(seeded_api, "assets", "valid.csv", content).json()
    assert (second["valid_rows"], second["duplicate_rows"]) == (0, 3)
    seeded_api.post(f"/api/imports/{second['id']}/commit")
    assert count(seeded, Asset) == after_first


def test_commit_rechecks_rows_that_became_duplicates(
    seeded_api: TestClient, seeded: Session
) -> None:
    """Two previews of the same file: committing the first makes the second's rows duplicates."""
    sign_in(seeded_api, "omotayo")
    content = sample("assets_import_valid.csv")
    a = upload(seeded_api, "assets", "a.csv", content).json()
    b = upload(seeded_api, "assets", "b.csv", content).json()
    assert b["valid_rows"] == 3  # both previews looked fine
    seeded_api.post(f"/api/imports/{a['id']}/commit")
    late = seeded_api.post(f"/api/imports/{b['id']}/commit").json()
    assert (late["valid_rows"], late["duplicate_rows"]) == (0, 3)


def test_risk_import_with_scores(seeded_api: TestClient, seeded: Session) -> None:
    sign_in(seeded_api, "omotayo")
    content = (
        b"title,asset_codes,owner_username,likelihood,impact,threat,vulnerability,business_impact,"
        b"rationale\n"
        b"Referral points farming by bots,A-001;A-004,emmanuel,3,4,Bots,No rate limit,Losses,"
        b"Seen at two peer fintechs this year.\n"
        b"Bad risk row,A-999,omotayo,6,2,t,v,i,\n"
        b"Credential stuffing and BVN lookup abuse on the KYC API,A-013,gilbert,,,t,v,i,\n"
    )
    batch = upload(seeded_api, "risks", "risks.csv", content).json()
    statuses = [(r["row"], r["status"]) for r in batch["rows"]]
    assert statuses == [(2, "valid"), (3, "rejected"), (4, "duplicate")]
    bad = " ".join(batch["rows"][1]["reasons"])
    assert bad == "likelihood: Input should be less than or equal to 5"
    committed = seeded_api.post(f"/api/imports/{batch['id']}/commit").json()
    code = committed["rows"][0]["created"]
    risk = seeded_api.get("/api/risks", params={"q": "Referral points"}).json()["items"][0]
    assert risk["risk_code"] == code == "R-023" and risk["current"]["score"] == 12


@pytest.mark.parametrize(
    ("name", "content", "message"),
    [
        ("assets.csv", b"", "empty"),
        ("assets.csv", b"name,colour\nx,red\n", "Unknown column(s): colour"),
        ("assets.csv", b"name,asset_type\nx,api\n", "Missing required column(s): service_code"),
        ("assets.csv", b"name,asset_type,service_code\n", "no data rows"),
        ("assets.xlsx", b"name,asset_type,service_code\n", "Upload a .csv file"),
    ],
)
def test_unreadable_files_rejected_whole(
    seeded_api: TestClient, name: str, content: bytes, message: str
) -> None:
    sign_in(seeded_api, "omotayo")
    response = upload(seeded_api, "assets", name, content)
    assert response.status_code == 422 and message in response.json()["detail"]


def test_headers_are_normalised(seeded_api: TestClient) -> None:
    sign_in(seeded_api, "omotayo")
    content = b"Name,Asset Type,SERVICE-CODE\nPartner API sandbox,api,S1\n"
    assert upload(seeded_api, "assets", "x.csv", content).json()["valid_rows"] == 1


def test_permissions(seeded_api: TestClient) -> None:
    content = sample("assets_import_valid.csv")
    for who in ("emmanuel", "kelechi", "ernestina"):
        seeded_api.cookies.clear()
        sign_in(seeded_api, who)
        assert upload(seeded_api, "assets", "a.csv", content).status_code == 403
        assert seeded_api.get("/api/imports").status_code == 403
    seeded_api.cookies.clear()
    sign_in(seeded_api, "admin")  # admins import assets but not risks (they can't assess)
    assert upload(seeded_api, "assets", "a.csv", content).status_code == 201
    risks = (
        b"title,asset_codes,owner_username,threat,vulnerability,business_impact\n"
        b"X risk,A-001,emmanuel,t,v,i\n"
    )
    assert upload(seeded_api, "risks", "r.csv", risks).status_code == 403


def test_cancel_and_finished_batches(seeded_api: TestClient, seeded: Session) -> None:
    sign_in(seeded_api, "omotayo")
    batch = upload(seeded_api, "assets", "a.csv", sample("assets_import_valid.csv")).json()
    cancelled = seeded_api.post(f"/api/imports/{batch['id']}/cancel").json()
    assert cancelled["status"] == "cancelled"
    assert seeded_api.post(f"/api/imports/{batch['id']}/commit").status_code == 409
    assert seeded_api.post(f"/api/imports/{batch['id']}/cancel").status_code == 409
    listed = seeded_api.get("/api/imports").json()
    assert listed[0]["id"] == batch["id"] and listed[0]["file_name"] == "a.csv"
    assert seeded_api.get(f"/api/imports/{batch['id']}").json()["status"] == "cancelled"
    assert seeded_api.get("/api/imports/999999").status_code == 404
    assert count(seeded, Risk) == 22


def test_sample_files_exist() -> None:
    for name in ("assets_import_valid.csv", "assets_import_with_errors.csv"):
        assert Path(SAMPLE_DIR / name).is_file()
