"""Accounts and logins: the tables, and every form of an account the API reads
or returns (registration, profile, tokens, passwords, admin management)."""

from datetime import datetime
from typing import TYPE_CHECKING, Annotated, Literal, Optional

import pydantic
from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, field_validator
from sqlalchemy import Text
from sqlmodel import Field, Relationship

from app.core.validation import validate_password_strength
from app.models.base import TIMESTAMP, SQLModel, timestamp_field

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.session import DDSession


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    # Stored lowercase (schemas/user.py): PostgreSQL compares text case-sensitively.
    email: str = Field(max_length=255, unique=True, index=True)
    username: str = Field(max_length=100, unique=True, index=True)
    password_hash: str = Field(max_length=255)
    full_name: str | None = Field(default=None, max_length=255)
    company: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    role: str | None = Field(default="analyst", max_length=50)  # schemas.user.Role
    is_active: bool | None = Field(default=True)
    is_verified: bool | None = Field(default=False)
    last_login: datetime | None = Field(default=None, sa_type=TIMESTAMP)
    created_at: datetime | None = timestamp_field()
    updated_at: datetime | None = timestamp_field(created=False, updated=True)

    sessions_created: list["DDSession"] = Relationship(
        back_populates="creator", sa_relationship_kwargs={"foreign_keys": "DDSession.created_by"}
    )
    sessions_assigned: list["DDSession"] = Relationship(
        back_populates="assignee", sa_relationship_kwargs={"foreign_keys": "DDSession.assigned_to"}
    )
    companies_created: list["Company"] = Relationship(
        back_populates="creator", sa_relationship_kwargs={"foreign_keys": "Company.created_by"}
    )
    companies_updated: list["Company"] = Relationship(
        back_populates="updater", sa_relationship_kwargs={"foreign_keys": "Company.updated_by"}
    )


class UserSession(SQLModel, table=True):
    """One login. Tokens are never stored: only their SHA-256 (security.hash_token),
    so a copy of this table cannot be replayed."""

    __tablename__ = "user_sessions"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int | None = Field(
        default=None, foreign_key="users.id", ondelete="CASCADE", index=True
    )
    access_token_hash: str = Field(max_length=64, unique=True)
    refresh_token_hash: str | None = Field(default=None, max_length=64, unique=True)
    expires_at: datetime = Field(sa_type=TIMESTAMP)
    ip_address: str | None = Field(default=None, max_length=45)  # fits IPv6
    user_agent: str | None = Field(default=None, sa_type=Text)
    created_at: datetime | None = timestamp_field()

    user: Optional["User"] = Relationship()


# --- What the API reads and returns ---------------------------------------------
# Pydantic's Field, not SQLModel's: SQLModel ignores `pattern` (and `regex`).

Role = Literal["admin", "analyst"]

# Email addresses are stored and compared lowercase: PostgreSQL compares text
# case-sensitively, so Jane@x.com and jane@x.com would otherwise be two accounts.
Email = Annotated[EmailStr, AfterValidator(lambda value: value.strip().lower())]


class UserProfile(BaseModel):
    """What a person says about themselves, without any privilege."""

    email: Email
    username: str = pydantic.Field(..., min_length=3, max_length=30, pattern="^[a-zA-Z0-9._-]+$")
    full_name: str | None = None
    company: str | None = None
    phone: str | None = None


class UserBase(UserProfile):
    role: Role = "analyst"


class UserCreate(UserBase):
    """A new account, role included: made by an admin (POST /admin/users) or
    by the create-admin command. There is no self-registration. The password
    is a provisional one, which the user changes in their profile. Unknown
    fields are refused rather than ignored."""

    model_config = ConfigDict(extra="forbid")

    password: str = pydantic.Field(..., min_length=8)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_strength(v)


class UserUpdate(BaseModel):
    full_name: str | None = None
    company: str | None = None
    phone: str | None = None
    email: Email | None = None


class UserResponse(UserBase):
    """An account, as the API returns it."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime | None
    last_login: datetime | None


class Token(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Body of POST /auth/refresh: the token travels in the body, never in the
    URL, where proxies and server logs would record it."""

    refresh_token: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = pydantic.Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_strength(v)


class PasswordReset(BaseModel):
    email: Email


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = pydantic.Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_strength(v)


# --- Admin ----------------------------------------------------------------------


class UserListItem(BaseModel):
    """User information for admin list view"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    full_name: str | None
    company: str | None
    role: str
    is_active: bool
    is_verified: bool
    last_login: datetime | None
    created_at: datetime


class UserListResponse(BaseModel):
    """Paginated user list response"""

    users: list[UserListItem]
    total: int
    page: int
    per_page: int
    total_pages: int


class UserRoleUpdate(BaseModel):
    """Schema for updating user role (anything but admin/analyst is a 422)"""

    model_config = ConfigDict(json_schema_extra={"example": {"role": "admin"}})

    role: Role


class UserStatusUpdate(BaseModel):
    """Schema for updating user status"""

    model_config = ConfigDict(json_schema_extra={"example": {"is_active": True}})

    is_active: bool


class AdminActionResponse(BaseModel):
    """Standard response for admin actions"""

    success: bool
    message: str
    user_id: int | None = None
