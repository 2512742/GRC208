"""Request authentication and authorisation (FastAPI dependencies).

- `get_auth`: resolves the session cookie to a signed-in user (401 otherwise) and, for every
  state-changing method, checks the CSRF header (403 otherwise; test T23).
- `require(perm)`: role-level permission check for a route.
- `ensure(...)`: record-level check inside a route (ownership, separation of duties).

Every 403 writes a DENIED audit entry with the reason, so attempts to approve one's own risk or
to edit as an auditor are visible to Internal Audit (tests T12, T19, T20). 401s are not audited:
anonymous noise would flood the log; failed *logins* are audited separately.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta

from fastapi import Depends, HTTPException, Request, status
from sqlmodel import Session, select

from app.core.config import Settings, get_settings
from app.core.permissions import Actor, Perm, Target, authorize, role_permissions
from app.core.security import csrf_matches, csrf_token_for, token_hash
from app.db import get_session
from app.models import User, UserSession
from app.models.enums import AuditAction, Role
from app.services import audit
from app.services.clock import now_utc

SESSION_COOKIE = "risktrack_session"
CSRF_COOKIE = "risktrack_csrf"
CSRF_HEADER = "X-CSRF-Token"
MUST_CHANGE_PASSWORD = "Change your password before continuing."  # noqa: S105 (message)
PASSWORD_CHANGE_ROUTES = frozenset(
    {
        "/api/me",
        "/api/me/password",
        "/api/me/security",
        "/api/me/preferences",
        "/api/auth/logout",
    }
)
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
LAST_SEEN_WRITE_INTERVAL = timedelta(minutes=5)  # avoid a database write on every request

NOT_SIGNED_IN = "Not signed in, or your session has expired."


def client_ip(request: Request, settings: Settings) -> str | None:
    if settings.trusts_proxy:
        forwarded = request.headers.get("x-forwarded-for", "")
        first = forwarded.split(",")[0].strip()
        if first:
            return first[:45]
    return request.client.host[:45] if request.client else None


@dataclass
class AuthContext:
    user: User
    session: UserSession
    csrf_token: str
    ip: str | None

    @property
    def actor(self) -> Actor:
        return Actor(
            user_id=self.user.id or 0, role=Role(self.user.role), is_active=self.user.is_active
        )

    @property
    def audit_actor(self) -> audit.AuditActor:
        return audit.AuditActor(
            user_id=self.user.id, username=self.user.username, role=self.user.role, ip=self.ip
        )


def get_auth(
    request: Request,
    db: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AuthContext:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, NOT_SIGNED_IN)

    row = db.exec(select(UserSession).where(UserSession.token_hash == token_hash(token))).first()
    now = now_utc()
    if (
        row is None
        or row.revoked_at is not None
        or row.expires_at <= now
        or row.last_seen_at + timedelta(minutes=settings.session_idle_minutes) <= now
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, NOT_SIGNED_IN)

    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, NOT_SIGNED_IN)

    ctx = AuthContext(
        user=user,
        session=row,
        csrf_token=csrf_token_for(token, settings.secret_key.get_secret_value()),
        ip=client_ip(request, settings),
    )

    # After an administrator sets a password, nothing works until the user replaces it
    # (Sentinel's must_change_password). The few routes needed to do that stay open.
    if user.must_change_password and request.url.path not in PASSWORD_CHANGE_ROUTES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, MUST_CHANGE_PASSWORD)

    if request.method not in SAFE_METHODS and not csrf_matches(
        request.headers.get(CSRF_HEADER), ctx.csrf_token
    ):
        deny(
            db, ctx, "Missing or invalid CSRF token.", detail=f"{request.method} {request.url.path}"
        )

    if now - row.last_seen_at >= LAST_SEEN_WRITE_INTERVAL:
        row.last_seen_at = now
        db.add(row)
        db.commit()
    return ctx


def deny(
    db: Session,
    ctx: AuthContext,
    reason: str,
    *,
    object_type: str | None = None,
    object_id: str | int | None = None,
    detail: str | None = None,
) -> None:
    """Record the refusal and stop the request with 403. Nothing else is pending at this point
    (checks run before any change), so committing only persists the audit entry."""
    db.rollback()
    audit.record(
        db,
        AuditAction.DENIED,
        ctx.audit_actor,
        object_type=object_type,
        object_id=object_id,
        detail=f"{reason} {detail}".strip() if detail else reason,
    )
    db.commit()
    raise HTTPException(status.HTTP_403_FORBIDDEN, reason)


def ensure(
    db: Session,
    ctx: AuthContext,
    perm: Perm,
    target: Target | None = None,
    *,
    object_type: str | None = None,
    object_id: str | int | None = None,
) -> None:
    """Record-level check; 403 + DENIED audit entry when refused."""
    decision = authorize(ctx.actor, perm, target)
    if not decision:
        deny(
            db,
            ctx,
            decision.reason,
            object_type=object_type,
            object_id=object_id,
            detail=f"[{perm.value}]",
        )


def require(perm: Perm) -> Callable[..., AuthContext]:
    """Route dependency for permissions that don't depend on a specific record (user admin,
    settings, audit log). Record-scoped actions use `ensure()` with the record instead."""

    def dependency(
        request: Request,
        ctx: AuthContext = Depends(get_auth),
        db: Session = Depends(get_session),
    ) -> AuthContext:
        if perm not in role_permissions(ctx.actor.role):
            deny(
                db,
                ctx,
                f"The {ctx.user.role} role cannot do this.",
                detail=f"[{perm.value}] {request.method} {request.url.path}",
            )
        return ctx

    return dependency
