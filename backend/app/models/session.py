import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Index, Text
from sqlmodel import Field, Relationship

from app.models.base import SQLModel, enum_type, timestamp_field

if TYPE_CHECKING:
    from app.models.answer import DDAnswer
    from app.models.company import Company
    from app.models.execution import DDExecution
    from app.models.user import User


class SessionStatus(str, enum.Enum):
    CREATED = "created"
    DOCUMENTS_UPLOADED = "documents_uploaded"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class DDSession(SQLModel, table=True):
    __tablename__ = "dd_sessions"
    __table_args__ = (Index("ix_dd_sessions_company_status", "company_id", "status"),)

    id: int | None = Field(default=None, primary_key=True)
    session_code: str | None = Field(default=None, max_length=50, unique=True, index=True)
    company_id: int = Field(foreign_key="companies.id")
    name: str = Field(max_length=255)
    description: str | None = Field(default=None, sa_type=Text)
    status: SessionStatus | None = Field(
        default=SessionStatus.CREATED, sa_type=enum_type(SessionStatus, "session_status")
    )
    created_by: int | None = Field(default=None, foreign_key="users.id", index=True)
    assigned_to: int | None = Field(default=None, foreign_key="users.id", index=True)

    # DD types selected for this session: a JSON array of DD type ids. Binds the
    # session to them even as the DD types evolve.
    dd_types_json: str | None = Field(default=None, sa_type=Text)

    created_at: datetime | None = timestamp_field()
    updated_at: datetime | None = timestamp_field(updated=True)

    company: Optional["Company"] = Relationship(back_populates="sessions")
    answers: list["DDAnswer"] = Relationship(back_populates="session")
    creator: Optional["User"] = Relationship(
        back_populates="sessions_created",
        sa_relationship_kwargs={"foreign_keys": "DDSession.created_by"},
    )
    assignee: Optional["User"] = Relationship(
        back_populates="sessions_assigned",
        sa_relationship_kwargs={"foreign_keys": "DDSession.assigned_to"},
    )
    executions: list["DDExecution"] = Relationship(
        back_populates="session", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
