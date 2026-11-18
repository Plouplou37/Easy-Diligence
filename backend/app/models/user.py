from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Text
from sqlmodel import Field, Relationship

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
