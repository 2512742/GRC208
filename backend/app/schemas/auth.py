"""Request and response bodies for authentication, the current user and user admin."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.timezones import DISPLAY_TIMEZONES, is_allowed
from app.models.enums import Role

USERNAME_PATTERN = r"^[a-z0-9][a-z0-9._-]{2,49}$"
# Deliberately simple: one @, something on each side, a dot in the domain, no spaces.
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


def _normalise_username(value: str) -> str:
    return value.strip().lower()


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=256)

    @field_validator("username")
    @classmethod
    def _normalise(cls, value: str) -> str:
        return _normalise_username(value)


class UserSummary(BaseModel):
    """Public view of a user: what owner dropdowns and record pages show."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str
    role: Role
    job_title: str | None
    department: str | None
    is_active: bool


class UserDetail(UserSummary):
    email: str | None
    display_timezone: str
    created_at: datetime
    last_login_at: datetime | None


class Me(UserDetail):
    permissions: list[str]
    csrf_token: str


class PreferencesUpdate(BaseModel):
    display_timezone: str

    @field_validator("display_timezone")
    @classmethod
    def _allowed_zone(cls, value: str) -> str:
        if not is_allowed(value):
            raise ValueError(f"must be one of: {', '.join(DISPLAY_TIMEZONES)}")
        return value


class TimezoneOption(BaseModel):
    value: str
    label: str


class UserCreate(BaseModel):
    username: str = Field(pattern=USERNAME_PATTERN)
    full_name: str = Field(min_length=2, max_length=120)
    email: str | None = Field(default=None, max_length=254, pattern=EMAIL_PATTERN)
    role: Role
    job_title: str | None = Field(default=None, max_length=120)
    department: str | None = Field(default=None, max_length=120)
    password: str = Field(min_length=1, max_length=256)

    @field_validator("username", mode="before")
    @classmethod
    def _normalise(cls, value: object) -> object:
        return _normalise_username(value) if isinstance(value, str) else value


class UserUpdate(BaseModel):
    """Admin changes. Omitted fields stay as they are."""

    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    email: str | None = Field(default=None, max_length=254, pattern=EMAIL_PATTERN)
    role: Role | None = None
    job_title: str | None = Field(default=None, max_length=120)
    department: str | None = Field(default=None, max_length=120)
    is_active: bool | None = None
    new_password: str | None = Field(default=None, min_length=1, max_length=256)
