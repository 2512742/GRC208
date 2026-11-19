"""Users and login sessions."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint
from sqlmodel import Field, SQLModel

from app.models.base import UTCDateTime, allowed
from app.models.enums import Role
from app.services.clock import now_utc


class User(SQLModel, table=True):
    __tablename__ = "user_account"  # "user" is reserved in PostgreSQL
    __table_args__ = (
        allowed("role", Role),
        CheckConstraint("length(username) >= 3", name="username_length"),
    )

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(max_length=50, unique=True, index=True)
    full_name: str = Field(max_length=120)
    email: str | None = Field(default=None, max_length=254, unique=True)
    password_hash: str = Field(max_length=255)
    role: str = Field(max_length=20)
    job_title: str | None = Field(default=None, max_length=120)
    department: str | None = Field(default=None, max_length=120)
    # "system" (use the device's zone) or an IANA zone from the allow-list in PLAN.md §2.7.
    display_timezone: str = Field(default="system", max_length=64)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=now_utc, sa_type=UTCDateTime, nullable=False)
    last_login_at: datetime | None = Field(default=None, sa_type=UTCDateTime)


class UserSession(SQLModel, table=True):
    """Server-side session. The cookie holds a random token; only its SHA-256 is stored here."""

    __tablename__ = "user_session"

    id: int | None = Field(default=None, primary_key=True)
    token_hash: str = Field(max_length=64, unique=True, index=True)
    user_id: int = Field(foreign_key="user_account.id", ondelete="CASCADE", index=True)
    created_at: datetime = Field(default_factory=now_utc, sa_type=UTCDateTime, nullable=False)
    expires_at: datetime = Field(sa_type=UTCDateTime, nullable=False)
    last_seen_at: datetime = Field(default_factory=now_utc, sa_type=UTCDateTime, nullable=False)
    revoked_at: datetime | None = Field(default=None, sa_type=UTCDateTime)
    ip: str | None = Field(default=None, max_length=45)
    user_agent: str | None = Field(default=None, max_length=255)
