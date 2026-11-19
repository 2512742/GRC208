"""Creating and changing users: shared by the admin API, the CLI and the demo seed."""

from __future__ import annotations

from sqlmodel import Session, func, select

from app.core.security import hash_password, password_problems
from app.models import User
from app.models.enums import AuditAction, Role
from app.services import audit


class UserError(ValueError):
    """A request that can't be applied; the message is safe to show."""


def username_taken(session: Session, username: str) -> bool:
    return (
        session.exec(select(User.id).where(func.lower(User.username) == username.lower())).first()
        is not None
    )


def email_taken(session: Session, email: str, except_id: int | None = None) -> bool:
    query = select(User.id).where(func.lower(User.email) == email.lower())
    if except_id is not None:
        query = query.where(User.id != except_id)
    return session.exec(query).first() is not None


def check_password(password: str, username: str) -> None:
    problems = password_problems(password, username)
    if problems:
        raise UserError("Password needs: " + "; ".join(problems) + ".")


def create_user(
    session: Session,
    *,
    username: str,
    full_name: str,
    role: Role,
    password: str,
    email: str | None = None,
    job_title: str | None = None,
    department: str | None = None,
    by: audit.AuditActor = audit.SYSTEM,
) -> User:
    username = username.strip().lower()
    if username_taken(session, username):
        raise UserError(f"The username '{username}' is already taken.")
    if email and email_taken(session, email):
        raise UserError("That email address is already used by another account.")
    check_password(password, username)
    user = User(
        username=username,
        full_name=full_name.strip(),
        email=email,
        role=Role(role).value,
        job_title=job_title,
        department=department,
        password_hash=hash_password(password),
    )
    session.add(user)
    session.flush()
    audit.record(
        session,
        AuditAction.CREATE,
        by,
        object_type="user",
        object_id=user.id,
        after=public_fields(user),
    )
    return user


def public_fields(user: User) -> dict[str, object]:
    """What the audit log records about a user (never the password hash)."""
    return {
        "username": user.username,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "job_title": user.job_title,
        "department": user.department,
        "is_active": user.is_active,
    }
