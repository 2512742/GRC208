"""Self-service account security (borrowed from Sentinel, no email): password change, one-time
recovery code and "forgot password", forced change after an admin reset, sessions, activity."""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, col, select

from app.models import AuditLog, User
from tests.conftest import DEMO_PASSWORD, sign_in

NEW_PASSWORD = "Ledger-Locks-2026"
CODE_PATTERN = re.compile(r"^[A-HJ-NP-Z2-9]{5}(-[A-HJ-NP-Z2-9]{5}){3}$")


def another_client(api: TestClient) -> TestClient:
    """A second browser for the same app and database (its own cookie jar)."""
    return TestClient(api.app, base_url="https://testserver")


def user(db: Session, username: str) -> User:
    return db.exec(select(User).where(User.username == username)).one()


def entries(db: Session, action: str, username: str) -> list[AuditLog]:
    return list(
        db.exec(
            select(AuditLog)
            .where(AuditLog.action == action, AuditLog.username == username)
            .order_by(col(AuditLog.id))
        )
    )


# ── Password change ───────────────────────────────────────────────────────────────────────


def test_change_password_ends_other_sessions_only(
    api: TestClient, people: dict, db: Session
) -> None:
    phone = another_client(api)
    sign_in(phone, "omotayo")
    sign_in(api, "omotayo")

    changed = api.post(
        "/api/me/password", json={"current_password": DEMO_PASSWORD, "new_password": NEW_PASSWORD}
    )
    assert changed.status_code == 200, changed.text
    assert api.get("/api/me").status_code == 200  # this session stays signed in
    assert phone.get("/api/me").status_code == 401  # the other one is gone
    account = user(db, "omotayo")
    assert account.password_changed_at is not None and not account.must_change_password
    assert "1 other session(s) ended" in (entries(db, "UPDATE", "omotayo")[-1].detail or "")

    fresh = another_client(api)
    assert (
        fresh.post(
            "/api/auth/login", json={"username": "omotayo", "password": DEMO_PASSWORD}
        ).status_code
        == 401
    )
    sign_in(fresh, "omotayo", NEW_PASSWORD)


@pytest.mark.parametrize(
    ("current", "new", "status", "message"),
    [
        ("wrong-password", NEW_PASSWORD, 403, "current password is incorrect"),
        (DEMO_PASSWORD, "short", 422, "at least 10 characters"),
        (DEMO_PASSWORD, DEMO_PASSWORD, 422, "must differ from the current password"),
        (DEMO_PASSWORD, "omotayo-2026-secure", 422, "must not contain the username"),
    ],
)
def test_change_password_refusals(
    api: TestClient, people: dict, db: Session, current: str, new: str, status: int, message: str
) -> None:
    sign_in(api, "omotayo")
    response = api.post("/api/me/password", json={"current_password": current, "new_password": new})
    assert response.status_code == status and message in response.json()["detail"]


def test_wrong_current_password_counts_towards_lockout(
    api: TestClient, people: dict, db: Session
) -> None:
    sign_in(api, "omotayo")
    body = {"current_password": "guess-guess-guess", "new_password": NEW_PASSWORD}
    for _ in range(5):
        assert api.post("/api/me/password", json=body).status_code == 403
    assert len(entries(db, "LOGIN_FAILED", "omotayo")) == 5
    assert api.post("/api/me/password", json=body).status_code == 429
    security = api.get("/api/me/security").json()
    assert security["locked"] is True and security["recent_failed_sign_ins"] == 5


# ── Recovery code and forgot password ─────────────────────────────────────────────────────


def issue_code(api: TestClient) -> str:
    response = api.post("/api/me/recovery-code", json={"current_password": DEMO_PASSWORD})
    assert response.status_code == 201, response.text
    assert response.headers["cache-control"] == "no-store"
    return response.json()["code"]


def test_recovery_code_shown_once_stored_as_hash(
    api: TestClient, people: dict, db: Session
) -> None:
    sign_in(api, "emmanuel")
    assert api.get("/api/me/security").json()["has_recovery_code"] is False
    assert (
        api.post("/api/me/recovery-code", json={"current_password": "nope-nope"}).status_code == 403
    )
    code = issue_code(api)
    assert CODE_PATTERN.match(code)
    stored = user(db, "emmanuel")
    assert stored.recovery_code_hash and code not in stored.recovery_code_hash
    assert stored.recovery_code_hash.startswith("$argon2")
    log_text = " ".join(str(e.detail) + str(e.after) for e in db.exec(select(AuditLog)))
    assert code not in log_text and code.replace("-", "") not in log_text
    me = api.get("/api/me").json()
    assert me["has_recovery_code"] is True and "recovery_code_hash" not in me


def test_forgot_password_with_recovery_code(api: TestClient, people: dict, db: Session) -> None:
    laptop = another_client(api)
    sign_in(laptop, "emmanuel")
    sign_in(api, "emmanuel")
    old_code = issue_code(api)
    code = issue_code(api)  # replaces the first one
    api.cookies.clear()

    def recover(c: str, password: str = NEW_PASSWORD) -> int:
        return api.post(
            "/api/auth/recover", json={"username": "Emmanuel", "code": c, "new_password": password}
        ).status_code

    assert recover(old_code) == 401  # replaced codes no longer work
    assert recover(code, "weak") == 422  # valid code, weak password: code is kept
    assert recover(code.lower().replace("-", " ")) == 204  # forgiving about case and dashes
    assert recover(code) == 401  # used up
    assert laptop.get("/api/me").status_code == 401  # every session ended
    stored = user(db, "emmanuel")
    assert stored.recovery_code_hash is None and not stored.must_change_password
    sign_in(api, "emmanuel", NEW_PASSWORD)
    assert "recovery code" in (entries(db, "UPDATE", "emmanuel")[-1].detail or "")


def test_recovery_errors_are_identical_and_throttled(
    api: TestClient, people: dict, db: Session
) -> None:
    sign_in(api, "anita")
    code = issue_code(api)
    api.cookies.clear()
    unknown = api.post(
        "/api/auth/recover",
        json={"username": "nobody", "code": code, "new_password": NEW_PASSWORD},
    )
    no_code = api.post(
        "/api/auth/recover",
        json={"username": "kelechi", "code": code, "new_password": NEW_PASSWORD},
    )
    assert unknown.json() == no_code.json() == {"detail": "Incorrect username or recovery code."}
    for _ in range(5):
        api.post(
            "/api/auth/recover",
            json={
                "username": "anita",
                "code": "AAAAA-AAAAA-AAAAA-AAAAA",
                "new_password": NEW_PASSWORD,
            },
        )
    throttled = api.post(
        "/api/auth/recover", json={"username": "anita", "code": code, "new_password": NEW_PASSWORD}
    )
    assert throttled.status_code == 429  # even the right code waits out the lockout


def test_revoke_recovery_code(api: TestClient, people: dict, db: Session) -> None:
    sign_in(api, "anita")
    issue_code(api)
    response = api.request(
        "DELETE", "/api/me/recovery-code", json={"current_password": DEMO_PASSWORD}
    )
    assert response.status_code == 204
    assert user(db, "anita").recovery_code_hash is None


# ── Forced change after an administrator sets the password ────────────────────────────────


def test_admin_set_passwords_must_be_changed(api: TestClient, people: dict, db: Session) -> None:
    sign_in(api, "admin")
    created = api.post(
        "/api/users",
        json={
            "username": "new.analyst",
            "full_name": "New Analyst",
            "role": "analyst",
            "password": "Temporary-Pass-77",
        },
    ).json()
    assert created["must_change_password"] is True

    newcomer = another_client(api)
    sign_in(newcomer, "new.analyst", "Temporary-Pass-77")
    me = newcomer.get("/api/me").json()
    assert me["must_change_password"] is True
    blocked = newcomer.get("/api/risks")
    assert blocked.status_code == 403 and blocked.json()["detail"].startswith(
        "Change your password"
    )
    assert newcomer.get("/api/me/security").status_code == 200  # the change screen still works
    changed = newcomer.post(
        "/api/me/password",
        json={"current_password": "Temporary-Pass-77", "new_password": NEW_PASSWORD},
    )
    assert changed.status_code == 200 and changed.json()["must_change_password"] is False
    assert newcomer.get("/api/risks").status_code == 200

    # An admin reset forces another change and signs the user out.
    reset = api.patch(f"/api/users/{created['id']}", json={"new_password": "Another-Temp-88"})
    assert reset.json()["must_change_password"] is True
    assert newcomer.get("/api/me").status_code == 401


# ── Sessions ──────────────────────────────────────────────────────────────────────────────


def test_list_and_end_sessions(api: TestClient, people: dict, db: Session) -> None:
    phone = another_client(api)
    phone.headers["User-Agent"] = (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
    )
    sign_in(phone, "kelechi")
    sign_in(api, "kelechi")
    sessions = api.get("/api/me/sessions").json()
    assert len(sessions) == 2 and [s["current"] for s in sessions].count(True) == 1
    other = next(s for s in sessions if not s["current"])
    assert other["device"] == "Safari on iPhone"
    current = next(s for s in sessions if s["current"])
    assert api.delete(f"/api/me/sessions/{current['id']}").status_code == 409
    assert api.delete(f"/api/me/sessions/{other['id']}").status_code == 200
    assert phone.get("/api/me").status_code == 401

    # Someone else's session id looks exactly like a missing one (no IDOR).
    sign_in(phone, "adeola")
    adeola_session = phone.get("/api/me/sessions").json()[0]["id"]
    assert api.delete(f"/api/me/sessions/{adeola_session}").status_code == 404
    assert phone.get("/api/me").status_code == 200


def test_sign_out_others(api: TestClient, people: dict) -> None:
    devices = [another_client(api) for _ in range(2)]
    for d in devices:
        sign_in(d, "adeola")
    sign_in(api, "adeola")
    assert api.post("/api/me/sessions/sign-out-others").json() == {"sessions_ended": 2}
    assert all(d.get("/api/me").status_code == 401 for d in devices)
    assert api.get("/api/me").status_code == 200


# ── Profile and activity ──────────────────────────────────────────────────────────────────


def test_profile_update_cannot_touch_role(api: TestClient, people: dict, db: Session) -> None:
    sign_in(api, "ernestina")
    response = api.patch(
        "/api/me/profile",
        json={
            "job_title": "Head of Internal Audit",
            "email": "ernestina@alajo.example",
            "role": "admin",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["job_title"] == "Head of Internal Audit" and body["role"] == "auditor"
    assert "view_audit" in body["permissions"] and "manage_users" not in body["permissions"]
    api2 = another_client(api)
    sign_in(api2, "kelechi")
    taken = api2.patch("/api/me/profile", json={"email": "ERNESTINA@alajo.example"})
    assert taken.status_code == 422
    assert entries(db, "UPDATE", "ernestina")[-1].after["job_title"] == "Head of Internal Audit"  # type: ignore[index]


def test_activity_shows_only_my_account_events(api: TestClient, people: dict) -> None:
    api.post("/api/auth/login", json={"username": "omotayo", "password": "wrong-password"})
    other = another_client(api)
    sign_in(other, "kelechi")
    sign_in(api, "omotayo")
    activity = api.get("/api/me/activity").json()
    actions = [a["action"] for a in activity]
    assert actions[:2] == ["LOGIN", "LOGIN_FAILED"]
    assert activity[1]["detail"] == "wrong password"
    assert len(activity) == 2  # kelechi's sign-in isn't listed


# ── Admin view of an account ──────────────────────────────────────────────────────────────


def test_admin_security_view_and_sign_out_everywhere(api: TestClient, people: dict) -> None:
    target = another_client(api)
    sign_in(target, "anita")
    for _ in range(5):
        api.post("/api/auth/login", json={"username": "omotayo", "password": "nope-nope-nope"})
    sign_in(api, "admin")
    ids = {u["username"]: u["id"] for u in api.get("/api/users").json()}
    locked = api.get(f"/api/users/{ids['omotayo']}/security").json()
    assert locked["locked"] is True and locked["lockout_minutes"] == 15
    anita = api.get(f"/api/users/{ids['anita']}/security").json()
    assert anita["active_sessions"] == 1 and anita["has_recovery_code"] is False
    ended = api.post(f"/api/users/{ids['anita']}/sign-out-everywhere").json()
    assert ended == {"sessions_ended": 1} and target.get("/api/me").status_code == 401

    api.cookies.clear()
    sign_in(api, "kelechi")
    assert api.get(f"/api/users/{ids['anita']}/security").status_code == 403
    assert api.post(f"/api/users/{ids['anita']}/sign-out-everywhere").status_code == 403
