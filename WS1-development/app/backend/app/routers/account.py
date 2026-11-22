"""The signed-in user's own account: profile, password, recovery code, sessions, activity.

All routes act on the caller only; there is no user id in any path, so they can't be pointed
at someone else's account (IDOR-proof by construction).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session, col, select

from app.core.auth import AuthContext, get_auth
from app.core.config import Settings, get_settings
from app.core.security import PASSWORD_MIN_LENGTH, verify_password
from app.db import get_session
from app.models import AuditLog, User, UserSession
from app.models.enums import AuditAction
from app.routers.auth import build_me
from app.schemas.account import (
    ActivityOut,
    ConfirmPassword,
    PasswordChange,
    ProfileUpdate,
    RecoveryCodeOut,
    SecurityOverview,
    SessionOut,
    SignedOut,
)
from app.schemas.auth import Me
from app.services import account, audit
from app.services.clock import now_utc
from app.services.users import email_taken, public_fields

router = APIRouter(prefix="/me", tags=["my account"])

ACCOUNT_ACTIONS = (
    AuditAction.LOGIN,
    AuditAction.LOGIN_FAILED,
    AuditAction.LOGOUT,
    AuditAction.UPDATE,
)
WRONG_PASSWORD = "Your current password is incorrect."  # noqa: S105 (message)


def security_overview(db: Session, user: User, settings: Settings) -> SecurityOverview:
    failures = account.recent_failures(db, settings, username=user.username)
    return SecurityOverview(
        must_change_password=user.must_change_password,
        password_changed_at=user.password_changed_at,
        has_recovery_code=user.has_recovery_code,
        recovery_code_created_at=user.recovery_code_created_at,
        last_login_at=user.last_login_at,
        active_sessions=len(account.active_sessions(db, user.id or 0)),
        recent_failed_sign_ins=failures,
        locked=failures >= settings.login_max_failures,
        lockout_minutes=settings.login_lockout_minutes,
        lockout_after_failures=settings.login_max_failures,
        password_min_length=PASSWORD_MIN_LENGTH,
        session_hours=settings.session_hours,
        session_idle_minutes=settings.session_idle_minutes,
    )


def _confirm_password(db: Session, ctx: AuthContext, settings: Settings, given: str) -> None:
    """Re-check the password for a sensitive step. Wrong answers count towards the lockout."""
    if account.is_throttled(db, settings, ctx.user.username, ctx.ip):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Too many failed attempts. Try again in {settings.login_lockout_minutes} minutes.",
        )
    ok, _ = verify_password(given, ctx.user.password_hash)
    if not ok:
        audit.record(
            db,
            AuditAction.LOGIN_FAILED,
            ctx.audit_actor,
            object_type="user",
            object_id=ctx.user.id,
            detail="wrong current password on a sensitive account step",
        )
        db.commit()
        raise HTTPException(status.HTTP_403_FORBIDDEN, WRONG_PASSWORD)


@router.get("/security", response_model=SecurityOverview)
def my_security(
    ctx: AuthContext = Depends(get_auth),
    db: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> SecurityOverview:
    return security_overview(db, ctx.user, settings)


@router.patch("/profile", response_model=Me)
def update_profile(
    body: ProfileUpdate, ctx: AuthContext = Depends(get_auth), db: Session = Depends(get_session)
) -> Me:
    changes = body.model_dump(exclude_unset=True)
    if "full_name" in changes and not changes["full_name"]:
        changes.pop("full_name")
    for key in ("email", "job_title", "department"):
        if key in changes and isinstance(changes[key], str):
            changes[key] = changes[key].strip() or None
    if changes.get("email") and email_taken(db, changes["email"], except_id=ctx.user.id):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "That email address is already used by another account.",
        )
    before = public_fields(ctx.user)
    for field, value in changes.items():
        setattr(ctx.user, field, value)
    db.add(ctx.user)
    audit.record(
        db,
        AuditAction.UPDATE,
        ctx.audit_actor,
        object_type="user",
        object_id=ctx.user.id,
        before=before,
        after=public_fields(ctx.user),
        detail="profile updated by the user",
    )
    db.commit()
    db.refresh(ctx.user)
    return build_me(ctx.user, ctx.csrf_token)


@router.post("/password", response_model=Me)
def change_password(
    body: PasswordChange,
    ctx: AuthContext = Depends(get_auth),
    db: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Me:
    """Needs the current password. Other sessions end; this one stays signed in."""
    _confirm_password(db, ctx, settings, body.current_password)
    try:
        account.check_new_password(ctx.user, body.new_password, body.current_password)
    except account.AccountError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    was_forced = ctx.user.must_change_password
    account.set_password(db, ctx.user, body.new_password, must_change=False)
    ended = account.revoke_sessions(db, ctx.user.id or 0, keep_id=ctx.session.id)
    audit.record(
        db,
        AuditAction.UPDATE,
        ctx.audit_actor,
        object_type="user",
        object_id=ctx.user.id,
        detail=(
            f"password changed{' (required after an administrator reset)' if was_forced else ''}; "
            f"{ended} other session(s) ended"
        ),
    )
    db.commit()
    db.refresh(ctx.user)
    return build_me(ctx.user, ctx.csrf_token)


@router.post("/recovery-code", response_model=RecoveryCodeOut, status_code=status.HTTP_201_CREATED)
def create_recovery_code(
    body: ConfirmPassword,
    response: Response,
    ctx: AuthContext = Depends(get_auth),
    db: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> RecoveryCodeOut:
    """A new one-time code, shown once; any earlier code stops working immediately."""
    _confirm_password(db, ctx, settings, body.current_password)
    replaced = ctx.user.has_recovery_code
    code = account.issue_recovery_code(db, ctx.user)
    audit.record(
        db,
        AuditAction.UPDATE,
        ctx.audit_actor,
        object_type="user",
        object_id=ctx.user.id,
        detail="recovery code generated" + (" (previous code revoked)" if replaced else ""),
    )
    db.commit()
    response.headers["Cache-Control"] = "no-store"
    return RecoveryCodeOut(code=code, created_at=ctx.user.recovery_code_created_at or now_utc())


@router.delete("/recovery-code", status_code=status.HTTP_204_NO_CONTENT)
def delete_recovery_code(
    body: ConfirmPassword,
    ctx: AuthContext = Depends(get_auth),
    db: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    _confirm_password(db, ctx, settings, body.current_password)
    ctx.user.recovery_code_hash = None
    ctx.user.recovery_code_created_at = None
    db.add(ctx.user)
    audit.record(
        db,
        AuditAction.UPDATE,
        ctx.audit_actor,
        object_type="user",
        object_id=ctx.user.id,
        detail="recovery code revoked",
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/sessions", response_model=list[SessionOut])
def my_sessions(
    ctx: AuthContext = Depends(get_auth), db: Session = Depends(get_session)
) -> list[SessionOut]:
    return [
        SessionOut(
            id=row.id or 0,
            device=account.device_label(row.user_agent),
            ip=row.ip,
            created_at=row.created_at,
            last_seen_at=row.last_seen_at,
            expires_at=row.expires_at,
            current=row.id == ctx.session.id,
        )
        for row in account.active_sessions(db, ctx.user.id or 0)
    ]


@router.post("/sessions/sign-out-others", response_model=SignedOut)
def sign_out_others(
    ctx: AuthContext = Depends(get_auth), db: Session = Depends(get_session)
) -> SignedOut:
    ended = account.revoke_sessions(db, ctx.user.id or 0, keep_id=ctx.session.id)
    audit.record(
        db,
        AuditAction.LOGOUT,
        ctx.audit_actor,
        object_type="user",
        object_id=ctx.user.id,
        detail=f"signed out {ended} other session(s)",
    )
    db.commit()
    return SignedOut(sessions_ended=ended)


@router.delete("/sessions/{session_id}", response_model=SignedOut)
def sign_out_session(
    session_id: int, ctx: AuthContext = Depends(get_auth), db: Session = Depends(get_session)
) -> SignedOut:
    row = db.get(UserSession, session_id)
    # Someone else's session id answers exactly like a missing one.
    if row is None or row.user_id != ctx.user.id or row.revoked_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found.")
    if row.id == ctx.session.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "That is this session; use Sign out instead.")
    row.revoked_at = now_utc()
    db.add(row)
    audit.record(
        db,
        AuditAction.LOGOUT,
        ctx.audit_actor,
        object_type="user",
        object_id=ctx.user.id,
        detail=f"signed out session {row.id} ({account.device_label(row.user_agent)})",
    )
    db.commit()
    return SignedOut(sessions_ended=1)


@router.get("/activity", response_model=list[ActivityOut])
def my_activity(
    ctx: AuthContext = Depends(get_auth), db: Session = Depends(get_session)
) -> list[ActivityOut]:
    """The latest sign-ins, failed attempts and account changes, so users can spot misuse."""
    rows = db.exec(
        select(AuditLog)
        .where(
            AuditLog.username == ctx.user.username,
            col(AuditLog.action).in_([a.value for a in ACCOUNT_ACTIONS]),
            (AuditLog.object_type == "user") | (AuditLog.action == AuditAction.LOGIN_FAILED.value),
        )
        .order_by(col(AuditLog.id).desc())
        .limit(30)
    ).all()
    return [
        ActivityOut(
            id=r.id or 0, occurred_at=r.occurred_at, action=r.action, detail=r.detail, ip=r.ip
        )
        for r in rows
    ]
