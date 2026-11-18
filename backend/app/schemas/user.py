from datetime import datetime
from typing import Annotated, Literal, get_args

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.validation import validate_password_strength

Role = Literal["admin", "analyst"]
ROLES = get_args(Role)

# Email addresses are stored and compared lowercase: PostgreSQL compares text
# case-sensitively, so Jane@x.com and jane@x.com would otherwise be two accounts.
Email = Annotated[EmailStr, AfterValidator(lambda value: value.strip().lower())]


class UserProfile(BaseModel):
    """What a person says about themselves, without any privilege."""

    email: Email
    username: str = Field(..., min_length=3, max_length=30, pattern="^[a-zA-Z0-9._-]+$")
    full_name: str | None = None
    company: str | None = None
    phone: str | None = None


class UserBase(UserProfile):
    role: Role = "analyst"


class UserCreate(UserBase):
    """Server-side creation, role included (the create-admin command, tests)."""

    password: str = Field(..., min_length=8)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_strength(v)


class UserRegister(UserProfile):
    """Self-registration. There is no role field, and unknown fields are
    refused: a request carrying "role" gets a 422 instead of being trusted.
    A registered account is always an analyst."""

    model_config = ConfigDict(extra="forbid")

    password: str = Field(..., min_length=8)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_strength(v)


class UserUpdate(BaseModel):
    full_name: str | None = None
    company: str | None = None
    phone: str | None = None
    email: Email | None = None


class UserInDB(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime | None
    last_login: datetime | None


class User(UserInDB):
    pass


class UserLogin(BaseModel):
    email: Email
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Body of POST /auth/refresh: the token travels in the body, never in the
    URL, where proxies and server logs would record it."""

    refresh_token: str


class TokenData(BaseModel):
    user_id: int | None = None
    email: str | None = None
    role: str | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_strength(v)


class PasswordReset(BaseModel):
    email: Email


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_strength(v)
