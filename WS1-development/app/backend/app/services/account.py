"""Self-service account security: password changes, one-time recovery codes, sessions, throttling.

Borrowed from the Sentinel project's design, because RiskTrack has no email either:
- "Forgot password" can't send a link, so each user may keep **one recovery code**, generated
  while signed in, shown once, stored only as an Argon2 hash and burnt on use. A new code
  replaces the old one.
- A password set by an administrator (new account or reset) must be replaced at the next
  sign-in (`must_change_password`), so the administrator never knows a working password.
- Changing or resetting a password ends the user's other sessions.
- Failed sign-ins *and* failed recovery attempts count towards the same lockout, read from the
  audit log, so it holds across serverless instances.
"""

from __future__ import annotations

import secrets
from datetime import timedelta

from sqlmodel import Session, col, func, select

from app.core.config import Settings
from app.core.security import (
    burn_password_check,
    hash_password,
    password_problems,
    verify_password,
)
from app.models import AuditLog, User, UserSession
from app.models.enums import AuditAction
from app.services import audit
from app.services.clock import now_utc

# Unambiguous alphabet (no 0/O, 1/I/L): easy to copy from paper.
RECOVERY_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
RECOVERY_GROUPS = 4
RECOVERY_GROUP_LENGTH = 5  # 20 symbols from 31 ≈ 99 bits

GENERIC_RECOVERY_ERROR = "Incorrect username or recovery code."


class AccountError(ValueError):
    """A request that can't be applied; the message is safe to show."""


class RecoveryRejected(AccountError):
    """Same message for every failure (unknown user, no code, wrong code, disabled)."""


# ── Throttling ────────────────────────────────────────────────────────────────────────────


def recent_failures(
    db: Session, settings: Settings, *, username: str | None = None, ip: str | None = None
) -> int:
    since = now_utc() - timedelta(minutes=settings.login_lockout_minutes)
    query = (
        select(func.count())
        .select_from(AuditLog)
        .where(
            AuditLog.action == AuditAction.LOGIN_FAILED.value, col(AuditLog.occurred_at) >= since
        )
    )
    if username is not None:
        query = query.where(AuditLog.username == username)
    if ip is not None:
        query = query.where(AuditLog.ip == ip)
    return db.exec(query).one()


def is_throttled(db: Session, settings: Settings, username: str, ip: str | None) -> bool:
    return recent_failures(db, settings, username=username) >= settings.login_max_failures or bool(
        ip and recent_failures(db, settings, ip=ip) >= settings.login_max_failures_per_ip
    )


# ── Password policy ───────────────────────────────────────────────────────────────────────


def check_new_password(user: User, new_password: str, current_password: str | None = None) -> None:
    problems = password_problems(new_password, user.username)
    if current_password is not None and new_password == current_password:
        problems.append("must differ from the current password")
    if problems:
        raise AccountError("The new password needs: " + "; ".join(problems) + ".")


def set_password(db: Session, user: User, new_password: str, *, must_change: bool) -> None:
    user.password_hash = hash_password(new_password)
    user.must_change_password = must_change
    user.password_changed_at = now_utc()
    db.add(user)


# ── Sessions ──────────────────────────────────────────────────────────────────────────────


def active_sessions(db: Session, user_id: int) -> list[UserSession]:
    now = now_utc()
    return list(
        db.exec(
            select(UserSession)
            .where(
                UserSession.user_id == user_id,
                col(UserSession.revoked_at).is_(None),
                col(UserSession.expires_at) > now,
            )
            .order_by(col(UserSession.last_seen_at).desc())
        )
    )


def revoke_sessions(db: Session, user_id: int, *, keep_id: int | None = None) -> int:
    """End every live session of the user except `keep_id`; returns how many were ended."""
    count = 0
    for row in active_sessions(db, user_id):
        if row.id != keep_id:
            row.revoked_at = now_utc()
            db.add(row)
            count += 1
    return count


def device_label(user_agent: str | None) -> str:
    """A short, human description of a browser user-agent ("Chrome on Android")."""
    ua = (user_agent or "").lower()
    if not ua:
        return "Unknown device"
    if "testclient" in ua or "python" in ua or "curl" in ua:
        return "Script or API client"
    browser = next(
        (
            name
            for key, name in (
                ("edg/", "Edge"),
                ("opr/", "Opera"),
                ("firefox", "Firefox"),
                ("crios", "Chrome"),
                ("chrome", "Chrome"),
                ("safari", "Safari"),
            )
            if key in ua
        ),
        "Browser",
    )
    system = next(
        (
            name
            for key, name in (
                ("iphone", "iPhone"),
                ("ipad", "iPad"),
                ("android", "Android"),
                ("windows", "Windows"),
                ("mac os", "macOS"),
                ("cros", "ChromeOS"),
                ("linux", "Linux"),
            )
            if key in ua
        ),
        "unknown system",
    )
    return f"{browser} on {system}"


# ── Recovery codes ────────────────────────────────────────────────────────────────────────


def _normalise_code(code: str) -> str:
    return "".join(ch for ch in code.upper() if ch.isalnum())


def new_recovery_code() -> str:
    symbols = "".join(
        secrets.choice(RECOVERY_ALPHABET) for _ in range(RECOVERY_GROUPS * RECOVERY_GROUP_LENGTH)
    )
    return "-".join(
        symbols[i : i + RECOVERY_GROUP_LENGTH]
        for i in range(0, len(symbols), RECOVERY_GROUP_LENGTH)
    )


def issue_recovery_code(db: Session, user: User) -> str:
    """Create or replace the user's code; the plaintext is returned once and never stored."""
    code = new_recovery_code()
    user.recovery_code_hash = hash_password(_normalise_code(code))
    user.recovery_code_created_at = now_utc()
    db.add(user)
    return code


def reset_with_recovery_code(
    db: Session, username: str, code: str, new_password: str, *, ip: str | None
) -> User:
    """Set a new password using the one-time code. Every failure looks the same to the caller;
    a valid code with a weak new password raises AccountError and keeps the code usable."""
    user = db.exec(select(User).where(func.lower(User.username) == username)).first()
    candidate = _normalise_code(code)
    if user is None or not user.is_active or user.recovery_code_hash is None:
        burn_password_check(candidate)  # same timing whatever the reason
        raise RecoveryRejected(GENERIC_RECOVERY_ERROR)
    ok, _ = verify_password(candidate, user.recovery_code_hash)
    if not ok:
        raise RecoveryRejected(GENERIC_RECOVERY_ERROR)
    check_new_password(user, new_password)
    set_password(db, user, new_password, must_change=False)
    user.recovery_code_hash = None
    user.recovery_code_created_at = None
    revoke_sessions(db, user.id or 0)
    audit.record(
        db,
        AuditAction.UPDATE,
        audit.AuditActor(user.id, user.username, user.role, ip),
        object_type="user",
        object_id=user.id,
        detail="password reset with a recovery code (code used up; all sessions ended)",
    )
    return user


def temporary_password() -> str:
    """For the offline CLI reset: readable, policy-compliant, must be changed at sign-in."""
    return new_recovery_code()
