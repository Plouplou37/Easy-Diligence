"""DD sessions: the table, and what the API reads and returns."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Index, Text
from sqlmodel import Field, Relationship

from app.core.pagination import PaginationMeta
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


class SessionBase(SQLModel):
    company_id: int = Field(foreign_key="companies.id")
    name: str = Field(max_length=255)
    description: str | None = Field(default=None, sa_type=Text)


class DDSession(SessionBase, table=True):
    __tablename__ = "dd_sessions"
    __table_args__ = (Index("ix_dd_sessions_company_status", "company_id", "status"),)

    id: int | None = Field(default=None, primary_key=True)
    session_code: str | None = Field(default=None, max_length=50, unique=True, index=True)
    status: SessionStatus | None = Field(
        default=SessionStatus.CREATED, sa_type=enum_type(SessionStatus, "session_status")
    )
    created_by: int | None = Field(default=None, foreign_key="users.id", index=True)
    assigned_to: int | None = Field(default=None, foreign_key="users.id", index=True)

    # The DD types chosen at creation, as JSON: [{"code", "name"}].
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


class SessionCreate(SessionBase):
    # The DD types to run; none means every active type the user can see.
    dd_type_ids: list[int] | None = None


class SessionResponse(SessionBase):
    id: int
    session_code: str | None = None
    status: SessionStatus
    created_at: datetime
    updated_at: datetime
    created_by: int | None = None
    assigned_to: int | None = None
    created_by_username: str | None = None
    dd_types_json: str | None = None  # the DD types chosen at creation, as JSON
    # The company under review, as two entities (see models/company.py): the
    # fund itself and the company running it.
    company_name: str | None = None
    management_company_name: str | None = None

    @classmethod
    def of(cls, session: DDSession) -> "SessionResponse":
        """The session, with its company's names and its creator's username."""
        response = cls.model_validate(session)
        if session.company is not None:
            response.company_name = session.company.name
            response.management_company_name = session.company.management_company_name
        if session.creator is not None:
            response.created_by_username = session.creator.username or session.creator.email
        return response


class SessionStatusResponse(SQLModel):
    id: int
    status: SessionStatus | None
    progress: list[dict[str, Any]]  # one entry per DD type run (services/sessions.py)


class SessionListResponse(SQLModel):
    sessions: list[SessionResponse]
    pagination: dict[str, Any]
    filters: dict[str, Any] | None = None

    @classmethod
    def of(
        cls, sessions: list[SessionResponse], meta: PaginationMeta, filters: dict[str, Any]
    ) -> "SessionListResponse":
        return cls(sessions=sessions, pagination=meta.model_dump(), filters=filters)
