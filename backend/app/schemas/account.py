"""Bodies for self-service account security and the admin's view of an account."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.auth import EMAIL_PATTERN, _normalise_username


class ProfileUpdate(BaseModel):
    """What users may change about themselves (role and username stay with the admin)."""

    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    email: str | None = Field(default=None, max_length=254, pattern=EMAIL_PATTERN)
    job_title: str | None = Field(default=None, max_length=120)
    department: str | None = Field(default=None, max_length=120)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=1, max_length=256)


class ConfirmPassword(BaseModel):
    """Re-entering the password before a sensitive step (e.g. a new recovery code)."""

    current_password: str = Field(min_length=1, max_length=256)


class RecoveryCodeOut(BaseModel):
    code: str = Field(description="Shown once. Only a hash is stored.")
    created_at: datetime


class RecoverRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    code: str = Field(min_length=1, max_length=64)
    new_password: str = Field(min_length=1, max_length=256)

    @field_validator("username")
    @classmethod
    def _normalise(cls, value: str) -> str:
        return _normalise_username(value)


class SessionOut(BaseModel):
    id: int
    device: str
    ip: str | None
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    current: bool


class ActivityOut(BaseModel):
    id: int
    occurred_at: datetime
    action: str
    detail: str | None
    ip: str | None


class SecurityOverview(BaseModel):
    """The signed-in user's own security status (also the admin's view of an account)."""

    must_change_password: bool
    password_changed_at: datetime | None
    has_recovery_code: bool
    recovery_code_created_at: datetime | None
    last_login_at: datetime | None
    active_sessions: int
    recent_failed_sign_ins: int
    locked: bool
    lockout_minutes: int
    lockout_after_failures: int
    password_min_length: int
    session_hours: int
    session_idle_minutes: int


class SignedOut(BaseModel):
    sessions_ended: int
