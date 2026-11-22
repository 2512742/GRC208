"""Sign-in, sign-out, the current user and their display preferences."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlmodel import Session, func, select

from app.core.auth import (
    CSRF_COOKIE,
    SESSION_COOKIE,
    AuthContext,
    client_ip,
    get_auth,
)
from app.core.config import Settings, get_settings
from app.core.permissions import role_permissions
from app.core.security import (
    burn_password_check,
    csrf_token_for,
    new_session_token,
    token_hash,
    verify_password,
)
from app.core.timezones import DISPLAY_TIMEZONES
from app.db import get_session
from app.models import User, UserSession
from app.models.enums import AuditAction, Role
from app.schemas.account import RecoverRequest
from app.schemas.auth import LoginRequest, Me, PreferencesUpdate, TimezoneOption
from app.services import account, audit
from app.services.clock import now_utc

router = APIRouter(tags=["auth"])

BAD_CREDENTIALS = "Incorrect username or password."
TOO_MANY = "Too many failed sign-in attempts. Try again in {minutes} minutes."


def build_me(user: User, csrf_token: str) -> Me:
    return Me(
        id=user.id or 0,
        username=user.username,
        full_name=user.full_name,
        role=Role(user.role),
        job_title=user.job_title,
        department=user.department,
        is_active=user.is_active,
        email=user.email,
        display_timezone=user.display_timezone,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        must_change_password=user.must_change_password,
        password_changed_at=user.password_changed_at,
        has_recovery_code=user.has_recovery_code,
        recovery_code_created_at=user.recovery_code_created_at,
        permissions=sorted(p.value for p in role_permissions(Role(user.role))),
        csrf_token=csrf_token,
    )


def _set_cookies(response: Response, token: str, csrf: str, settings: Settings) -> None:
    max_age = settings.session_hours * 3600
    common = {"max_age": max_age, "path": "/", "secure": settings.cookie_secure, "samesite": "lax"}
    response.set_cookie(SESSION_COOKIE, token, httponly=True, **common)  # type: ignore[arg-type]
    # Readable by the frontend so it can echo it in the X-CSRF-Token header.
    response.set_cookie(CSRF_COOKIE, csrf, httponly=False, **common)  # type: ignore[arg-type]


@router.post("/auth/login", response_model=Me)
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Me:
    ip = client_ip(request, settings)
    if account.is_throttled(db, settings, body.username, ip):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            TOO_MANY.format(minutes=settings.login_lockout_minutes),
        )

    user = db.exec(select(User).where(func.lower(User.username) == body.username)).first()
    if user is None:
        burn_password_check(body.password)  # same timing as a real check
        ok, upgraded = False, None
    else:
        ok, upgraded = verify_password(body.password, user.password_hash)

    if not ok or user is None or not user.is_active:
        reason = (
            "unknown user" if user is None else ("account disabled" if ok else "wrong password")
        )
        audit.record(
            db,
            AuditAction.LOGIN_FAILED,
            audit.AuditActor(
                user_id=user.id if user else None,
                username=body.username,
                role=user.role if user else None,
                ip=ip,
            ),
            detail=reason,
        )
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, BAD_CREDENTIALS)

    now = now_utc()
    token = new_session_token()
    db.add(
        UserSession(
            token_hash=token_hash(token),
            user_id=user.id,  # type: ignore[arg-type]
            created_at=now,
            last_seen_at=now,
            expires_at=now + timedelta(hours=settings.session_hours),
            ip=ip,
            user_agent=(request.headers.get("user-agent") or "")[:255] or None,
        )
    )
    if upgraded:
        user.password_hash = upgraded
    user.last_login_at = now
    db.add(user)
    audit.record(
        db,
        AuditAction.LOGIN,
        audit.AuditActor(user.id, user.username, user.role, ip),
        object_type="user",
        object_id=user.id,
    )
    db.commit()
    db.refresh(user)

    csrf = csrf_token_for(token, settings.secret_key.get_secret_value())
    _set_cookies(response, token, csrf, settings)
    return build_me(user, csrf)


@router.post("/auth/recover", status_code=status.HTTP_204_NO_CONTENT)
def recover(
    body: RecoverRequest,
    request: Request,
    db: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Forgot password: set a new one with the one-time recovery code (there is no email).

    Throttled together with sign-in; every rejection looks the same; success uses up the code
    and ends all of the account's sessions. Then sign in normally.
    """
    ip = client_ip(request, settings)
    if account.is_throttled(db, settings, body.username, ip):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            TOO_MANY.format(minutes=settings.login_lockout_minutes),
        )
    try:
        account.reset_with_recovery_code(db, body.username, body.code, body.new_password, ip=ip)
    except account.RecoveryRejected as exc:
        db.rollback()
        audit.record(
            db,
            AuditAction.LOGIN_FAILED,
            audit.AuditActor(user_id=None, username=body.username, role=None, ip=ip),
            detail="recovery code rejected",
        )
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    except account.AccountError as exc:
        db.rollback()  # valid code, weak password: the code stays usable
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    ctx: AuthContext = Depends(get_auth),
    db: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    ctx.session.revoked_at = now_utc()
    db.add(ctx.session)
    audit.record(db, AuditAction.LOGOUT, ctx.audit_actor, object_type="user", object_id=ctx.user.id)
    db.commit()
    response.status_code = status.HTTP_204_NO_CONTENT
    for name in (SESSION_COOKIE, CSRF_COOKIE):
        response.delete_cookie(name, path="/", secure=settings.cookie_secure, samesite="lax")
    return response


@router.get("/me", response_model=Me)
def me(ctx: AuthContext = Depends(get_auth)) -> Me:
    return build_me(ctx.user, ctx.csrf_token)


@router.patch("/me/preferences", response_model=Me)
def update_preferences(
    body: PreferencesUpdate,
    ctx: AuthContext = Depends(get_auth),
    db: Session = Depends(get_session),
) -> Me:
    before = {"display_timezone": ctx.user.display_timezone}
    ctx.user.display_timezone = body.display_timezone
    db.add(ctx.user)
    audit.record(
        db,
        AuditAction.UPDATE,
        ctx.audit_actor,
        object_type="user",
        object_id=ctx.user.id,
        before=before,
        after={"display_timezone": body.display_timezone},
    )
    db.commit()
    db.refresh(ctx.user)
    return build_me(ctx.user, ctx.csrf_token)


@router.get("/timezones", response_model=list[TimezoneOption])
def timezones() -> list[TimezoneOption]:
    """Choices for the display time-zone dropdown (public: the login page uses it too)."""
    return [TimezoneOption(value=v, label=label) for v, label in DISPLAY_TIMEZONES.items()]
