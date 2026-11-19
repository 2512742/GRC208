"""P3 auth API: sign-in, sessions, CSRF (T23), throttling, preferences, and audit trail."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, col, select

from app.core.auth import CSRF_COOKIE, SESSION_COOKIE
from app.models import AuditLog, User, UserSession
from app.services import clock
from tests.conftest import DEMO_PASSWORD, sign_in


def audit_actions(db: Session) -> list[tuple[str, str | None, str | None]]:
    rows = db.exec(select(AuditLog).order_by(col(AuditLog.id)))
    return [(r.action, r.username, r.detail) for r in rows]


# ── Sign-in ────────────────────────────────────────────────────────────────────────────────


def test_login_sets_secure_cookies_and_returns_profile(
    api: TestClient, people: dict, db: Session
) -> None:
    response = api.post("/api/auth/login", json={"username": "Omotayo ", "password": DEMO_PASSWORD})
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "omotayo" and body["role"] == "analyst"
    assert "assess_risk" in body["permissions"] and "decide_acceptance" not in body["permissions"]
    assert body["display_timezone"] == "system"
    assert "password_hash" not in body

    cookies = response.headers.get_list("set-cookie")
    session_cookie = next(c for c in cookies if c.startswith(SESSION_COOKIE + "="))
    csrf_cookie = next(c for c in cookies if c.startswith(CSRF_COOKIE + "="))
    for flag in ("HttpOnly", "Secure", "SameSite=lax", "Path=/"):
        assert flag.lower() in session_cookie.lower()
    assert "httponly" not in csrf_cookie.lower()  # the frontend must read it
    assert body["csrf_token"] in csrf_cookie

    stored = db.exec(select(UserSession)).one()
    assert stored.token_hash not in session_cookie  # only the hash is stored, not the token
    assert ("LOGIN", "omotayo", None) in audit_actions(db)


@pytest.mark.parametrize(
    ("username", "password", "why"),
    [
        ("omotayo", "wrong-password-123", "wrong password"),
        ("nobody", DEMO_PASSWORD, "unknown user"),
    ],
)
def test_failed_login_same_message_and_audited(
    api: TestClient, people: dict, db: Session, username: str, password: str, why: str
) -> None:
    response = api.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password."
    assert ("LOGIN_FAILED", username, why) in audit_actions(db)
    assert SESSION_COOKIE not in response.cookies


def test_disabled_account_cannot_sign_in(api: TestClient, people: dict, db: Session) -> None:
    people["anita"].is_active = False
    db.commit()
    response = api.post("/api/auth/login", json={"username": "anita", "password": DEMO_PASSWORD})
    assert response.status_code == 401
    assert ("LOGIN_FAILED", "anita", "account disabled") in audit_actions(db)


def test_lockout_after_five_failures_even_with_right_password(
    api: TestClient, people: dict
) -> None:
    for _ in range(5):
        api.post("/api/auth/login", json={"username": "emmanuel", "password": "nope-nope-nope"})
    blocked = api.post("/api/auth/login", json={"username": "emmanuel", "password": DEMO_PASSWORD})
    assert blocked.status_code == 429
    assert "Try again in 15 minutes" in blocked.json()["detail"]
    # Another account from the same address is unaffected (per-IP limit is higher).
    assert (
        api.post(
            "/api/auth/login", json={"username": "anita", "password": DEMO_PASSWORD}
        ).status_code
        == 200
    )


def test_lockout_expires_after_the_window(api: TestClient, people: dict) -> None:
    start = datetime(2026, 12, 1, 9, 0, tzinfo=UTC)
    with clock.frozen(start):
        for _ in range(5):
            api.post("/api/auth/login", json={"username": "emmanuel", "password": "nope-nope-nope"})
        assert (
            api.post(
                "/api/auth/login", json={"username": "emmanuel", "password": DEMO_PASSWORD}
            ).status_code
            == 429
        )
    with clock.frozen(start + timedelta(minutes=16)):
        assert (
            api.post(
                "/api/auth/login", json={"username": "emmanuel", "password": DEMO_PASSWORD}
            ).status_code
            == 200
        )


# ── Sessions ───────────────────────────────────────────────────────────────────────────────


def test_me_requires_a_session(api: TestClient) -> None:
    response = api.get("/api/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not signed in, or your session has expired."


def test_me_after_login_and_logout_revokes(api: TestClient, people: dict, db: Session) -> None:
    sign_in(api, "kelechi")
    me = api.get("/api/me")
    assert me.status_code == 200 and me.json()["full_name"] == "Kelechi Kenneth Nwankwo"
    assert api.post("/api/auth/logout").status_code == 204
    assert api.get("/api/me").status_code == 401
    assert db.exec(select(UserSession)).one().revoked_at is not None
    assert ("LOGOUT", "kelechi", None) in audit_actions(db)


def test_forged_session_cookie_rejected(api: TestClient, people: dict) -> None:
    api.cookies.set(SESSION_COOKIE, "made-up-token", domain="testserver")
    assert api.get("/api/me").status_code == 401


def test_session_expires_after_idle_timeout(api: TestClient, people: dict) -> None:
    start = datetime(2026, 12, 1, 9, 0, tzinfo=UTC)
    with clock.frozen(start):
        sign_in(api, "omotayo")
    with clock.frozen(start + timedelta(minutes=119)):
        assert api.get("/api/me").status_code == 200  # activity refreshes last_seen
    with clock.frozen(start + timedelta(minutes=119 + 121)):
        assert api.get("/api/me").status_code == 401  # 121 idle minutes


def test_session_has_an_absolute_lifetime(api: TestClient, people: dict) -> None:
    start = datetime(2026, 12, 1, 9, 0, tzinfo=UTC)
    with clock.frozen(start):
        sign_in(api, "omotayo")
    for hour in range(1, 12):  # stay active every hour...
        with clock.frozen(start + timedelta(hours=hour)):
            assert api.get("/api/me").status_code == 200
    with clock.frozen(start + timedelta(hours=12, minutes=1)):
        assert api.get("/api/me").status_code == 401  # ...but 12 hours is the limit


def test_disabling_a_user_ends_their_live_session(
    api: TestClient, people: dict, db: Session
) -> None:
    sign_in(api, "anita")
    people["anita"].is_active = False
    db.commit()
    assert api.get("/api/me").status_code == 401


# ── CSRF (T23) ─────────────────────────────────────────────────────────────────────────────


def test_t23_state_change_without_csrf_header_refused_and_audited(
    api: TestClient, people: dict, db: Session
) -> None:
    sign_in(api, "omotayo")
    del api.headers["X-CSRF-Token"]
    response = api.patch("/api/me/preferences", json={"display_timezone": "Africa/Kampala"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Missing or invalid CSRF token."
    denied = [a for a in audit_actions(db) if a[0] == "DENIED"]
    assert denied and denied[-1][1] == "omotayo" and "PATCH /api/me/preferences" in denied[-1][2]
    assert db.get(User, people["omotayo"].id).display_timezone == "system"


def test_t23_wrong_csrf_token_refused(api: TestClient, people: dict) -> None:
    sign_in(api, "omotayo")
    api.headers["X-CSRF-Token"] = "0" * 64
    assert api.post("/api/auth/logout").status_code == 403


def test_csrf_token_from_another_session_refused(api: TestClient, people: dict) -> None:
    other = sign_in(api, "anita")
    api.cookies.clear()
    sign_in(api, "omotayo")
    api.headers["X-CSRF-Token"] = other
    assert api.post("/api/auth/logout").status_code == 403


def test_reads_need_no_csrf_header(api: TestClient, people: dict) -> None:
    sign_in(api, "ernestina")
    del api.headers["X-CSRF-Token"]
    assert api.get("/api/me").status_code == 200


# ── Display time zone (T31, API part) ──────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "zone", ["Africa/Kampala", "Africa/Lagos", "Africa/Accra", "UTC", "system"]
)
def test_preference_saved_and_survives_relogin(api: TestClient, people: dict, zone: str) -> None:
    sign_in(api, "omotayo")
    response = api.patch("/api/me/preferences", json={"display_timezone": zone})
    assert response.status_code == 200 and response.json()["display_timezone"] == zone
    api.post("/api/auth/logout")
    api.cookies.clear()
    sign_in(api, "omotayo")
    assert api.get("/api/me").json()["display_timezone"] == zone


@pytest.mark.parametrize("zone", ["Europe/London", "Mars/Base", "", "africa/lagos"])
def test_zones_outside_the_allow_list_rejected(api: TestClient, people: dict, zone: str) -> None:
    sign_in(api, "omotayo")
    assert api.patch("/api/me/preferences", json={"display_timezone": zone}).status_code == 422


def test_timezone_choices_listed_publicly(api: TestClient) -> None:
    options = api.get("/api/timezones").json()
    values = [o["value"] for o in options]
    assert values[0] == "system"
    assert {"Africa/Lagos", "Africa/Kampala", "Africa/Accra", "UTC"} <= set(values)
