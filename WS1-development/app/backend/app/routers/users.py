"""Users: everyone signed in can list them (owner dropdowns); only admins change them."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, col, select

from app.core.auth import AuthContext, deny, get_auth, require
from app.core.config import Settings, get_settings
from app.core.permissions import Perm
from app.db import get_session
from app.models import User
from app.models.enums import AuditAction, Role
from app.routers.account import security_overview
from app.schemas.account import SecurityOverview, SignedOut
from app.schemas.auth import UserCreate, UserDetail, UserSummary, UserUpdate
from app.services import account, audit
from app.services.users import (
    UserError,
    check_password,
    create_user,
    email_taken,
    public_fields,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserSummary])
def list_users(
    role: Role | None = None,
    active: bool | None = None,
    _: AuthContext = Depends(get_auth),
    db: Session = Depends(get_session),
) -> list[User]:
    query = select(User).order_by(col(User.full_name))
    if role is not None:
        query = query.where(User.role == role.value)
    if active is not None:
        query = query.where(User.is_active == active)
    return list(db.exec(query))


@router.get("/{user_id}", response_model=UserDetail)
def get_user(
    user_id: int,
    _: AuthContext = Depends(require(Perm.MANAGE_USERS)),
    db: Session = Depends(get_session),
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")
    return user


@router.post("", response_model=UserDetail, status_code=status.HTTP_201_CREATED)
def add_user(
    body: UserCreate,
    ctx: AuthContext = Depends(require(Perm.MANAGE_USERS)),
    db: Session = Depends(get_session),
) -> User:
    try:
        # The administrator knows this password, so the user must replace it at first sign-in.
        user = create_user(db, **body.model_dump(), must_change_password=True, by=ctx.audit_actor)
    except UserError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserDetail)
def change_user(
    user_id: int,
    body: UserUpdate,
    ctx: AuthContext = Depends(require(Perm.MANAGE_USERS)),
    db: Session = Depends(get_session),
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")
    changes = body.model_dump(exclude_unset=True)

    if user.id == ctx.user.id and (
        changes.get("is_active") is False or changes.get("role", Role.ADMIN) != Role.ADMIN
    ):
        deny(
            db,
            ctx,
            "You cannot disable your own account or remove your own admin role.",
            object_type="user",
            object_id=user.id,
        )

    try:
        if changes.get("email") and email_taken(db, changes["email"], except_id=user.id):
            raise UserError("That email address is already used by another account.")
        new_password = changes.pop("new_password", None)
        if new_password is not None:
            check_password(new_password, user.username)
    except UserError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc

    before = public_fields(user)
    for field, value in changes.items():
        setattr(user, field, value.value if isinstance(value, Role) else value)
    if new_password is not None:
        account.set_password(db, user, new_password, must_change=True)
    db.add(user)

    # Disabling an account or resetting its password signs it out everywhere.
    if changes.get("is_active") is False or new_password is not None:
        account.revoke_sessions(db, user.id or 0)

    after = public_fields(user)
    audit.record(
        db,
        AuditAction.UPDATE,
        ctx.audit_actor,
        object_type="user",
        object_id=user.id,
        before=before,
        after=after,
        detail=(
            "password reset by an administrator (must be changed at next sign-in)"
            if new_password is not None
            else None
        ),
    )
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}/security", response_model=SecurityOverview)
def user_security(
    user_id: int,
    _: AuthContext = Depends(require(Perm.MANAGE_USERS)),
    db: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> SecurityOverview:
    """Account status for the admin: lockout, sessions, recovery code set (never the code)."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")
    return security_overview(db, user, settings)


@router.post("/{user_id}/sign-out-everywhere", response_model=SignedOut)
def sign_out_everywhere(
    user_id: int,
    ctx: AuthContext = Depends(require(Perm.MANAGE_USERS)),
    db: Session = Depends(get_session),
) -> SignedOut:
    """End every session of an account, e.g. after a lost phone or a suspected compromise."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")
    keep = ctx.session.id if user.id == ctx.user.id else None
    ended = account.revoke_sessions(db, user.id or 0, keep_id=keep)
    audit.record(
        db,
        AuditAction.LOGOUT,
        ctx.audit_actor,
        object_type="user",
        object_id=user.id,
        detail=f"administrator ended {ended} session(s) of {user.username}",
    )
    db.commit()
    return SignedOut(sessions_ended=ended)
