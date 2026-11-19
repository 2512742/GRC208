"""P3 user admin API and role refusals through HTTP (T19, T20 at API level)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, col, select

from app.core.security import verify_password
from app.models import AuditLog, User
from tests.conftest import sign_in

NEW_USER = {
    "username": "Maria.Nalima",
    "full_name": "Maria Nalima",
    "email": "maria@alajo.example",
    "role": "analyst",
    "job_title": "Risk Analyst",
    "password": "Treatment-Plan-2026",
}


def last_audit(db: Session) -> AuditLog:
    return db.exec(select(AuditLog).order_by(col(AuditLog.id).desc())).first()  # type: ignore[return-value]


def test_admin_creates_user_audited_without_password(
    api: TestClient, people: dict, db: Session
) -> None:
    sign_in(api, "admin")
    response = api.post("/api/users", json=NEW_USER)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["username"] == "maria.nalima" and body["role"] == "analyst"
    entry = last_audit(db)
    assert (entry.action, entry.object_type, entry.username) == ("CREATE", "user", "admin")
    assert "password" not in str(entry.after) and "hash" not in str(entry.after)
    created = db.get(User, body["id"])
    assert created is not None and verify_password(NEW_USER["password"], created.password_hash)[0]


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"username": "omotayo"}, "already taken"),
        ({"password": "short"}, "at least 10 characters"),
        ({"password": "maria.nalima-2026!"}, "must not contain the username"),
        ({"password": "aaaaaaaaaaaa"}, "5 different characters"),
    ],
)
def test_bad_new_users_rejected_with_reason(
    api: TestClient, people: dict, change: dict, message: str
) -> None:
    sign_in(api, "admin")
    response = api.post("/api/users", json={**NEW_USER, **change})
    assert response.status_code == 422
    assert message in response.json()["detail"]


@pytest.mark.parametrize(
    "change",
    [
        {"username": "x"},
        {"username": "has space"},
        {"role": "superuser"},
        {"email": "not-an-email"},
    ],
)
def test_invalid_fields_rejected_by_schema(api: TestClient, people: dict, change: dict) -> None:
    sign_in(api, "admin")
    assert api.post("/api/users", json={**NEW_USER, **change}).status_code == 422


@pytest.mark.parametrize("who", ["omotayo", "emmanuel", "kelechi", "ernestina"])
def test_t19_t20_non_admins_cannot_create_users_and_attempt_is_audited(
    api: TestClient, people: dict, db: Session, who: str
) -> None:
    sign_in(api, who)
    response = api.post("/api/users", json=NEW_USER)
    assert response.status_code == 403
    entry = last_audit(db)
    assert entry.action == "DENIED" and entry.username == who
    assert "[manage_users] POST /api/users" in (entry.detail or "")
    assert db.exec(select(User).where(User.username == "maria.nalima")).first() is None


def test_t19_auditor_cannot_change_a_user(api: TestClient, people: dict) -> None:
    sign_in(api, "ernestina")
    target = people["emmanuel"].id
    assert api.patch(f"/api/users/{target}", json={"role": "approver"}).status_code == 403


def test_everyone_signed_in_can_list_users_for_dropdowns(api: TestClient, people: dict) -> None:
    sign_in(api, "emmanuel")
    owners = api.get("/api/users", params={"role": "owner"}).json()
    assert {u["username"] for u in owners} == {"emmanuel", "anita"}
    assert all("email" not in u and "password_hash" not in u for u in owners)


def test_listing_users_needs_sign_in(api: TestClient, people: dict) -> None:
    assert api.get("/api/users").status_code == 401


def test_admin_changes_role_and_it_is_audited(api: TestClient, people: dict, db: Session) -> None:
    sign_in(api, "admin")
    target = people["anita"].id
    response = api.patch(f"/api/users/{target}", json={"role": "approver", "job_title": "CFO"})
    assert response.status_code == 200 and response.json()["role"] == "approver"
    entry = last_audit(db)
    assert entry.before["role"] == "owner" and entry.after["role"] == "approver"  # type: ignore[index]


def test_password_reset_signs_the_user_out(api: TestClient, people: dict) -> None:
    sign_in(api, "anita")
    anita_cookies = dict(api.cookies)
    api.cookies.clear()
    sign_in(api, "admin")
    target = people["anita"].id
    reset = api.patch(f"/api/users/{target}", json={"new_password": "Brand-New-Secret-77"})
    assert reset.status_code == 200
    api.cookies.clear()
    for name, value in anita_cookies.items():
        api.cookies.set(name, value, domain="testserver")
    assert api.get("/api/me").status_code == 401
    api.cookies.clear()
    sign_in(api, "anita", "Brand-New-Secret-77")


def test_admin_cannot_lock_themselves_out(api: TestClient, people: dict) -> None:
    sign_in(api, "admin")
    me = people["admin"].id
    assert api.patch(f"/api/users/{me}", json={"is_active": False}).status_code == 403
    assert api.patch(f"/api/users/{me}", json={"role": "analyst"}).status_code == 403
    assert api.patch(f"/api/users/{me}", json={"job_title": "Admin"}).status_code == 200


def test_unknown_user_is_404(api: TestClient, people: dict) -> None:
    sign_in(api, "admin")
    assert api.patch("/api/users/999999", json={"job_title": "x"}).status_code == 404
    assert api.get("/api/users/999999").status_code == 404


def test_duplicate_email_rejected(api: TestClient, people: dict) -> None:
    sign_in(api, "admin")
    assert api.post("/api/users", json=NEW_USER).status_code == 201
    other = {**NEW_USER, "username": "someone.else"}
    assert api.post("/api/users", json=other).status_code == 422
