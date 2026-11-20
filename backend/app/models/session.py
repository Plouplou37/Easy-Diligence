"""DD sessions: the table, the DD types chosen for each, and what the API reads
and returns.

A session has no status of its own: its state is that of its runs
(dd_executions), which the frontend derives (entities/execution) and the
deletion guard checks (services/sessions.py).
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Text
from sqlmodel import Field, Relationship

from app.core.pagination import PaginationMeta
from app.models.base import SQLModel, timestamp_field

if TYPE_CHECKING:
    from app.models.answer import DDAnswer
    from app.models.company import Company
    from app.models.dd_types import DDType
    from app.models.execution import DDExecution
    from app.models.user import User


class SessionBase(SQLModel):
    company_id: int = Field(foreign_key="companies.id", index=True)
    name: str = Field(max_length=255)
    description: str | None = Field(default=None, sa_type=Text)


class DDSession(SessionBase, table=True):
    __tablename__ = "dd_sessions"

    id: int | None = Field(default=None, primary_key=True)
    session_code: str | None = Field(default=None, max_length=50, unique=True, index=True)
    created_by: int | None = Field(default=None, foreign_key="users.id", index=True)
    assigned_to: int | None = Field(default=None, foreign_key="users.id", index=True)
    created_at: datetime = timestamp_field(nullable=False)
    updated_at: datetime = timestamp_field(updated=True, nullable=False)

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
    # The DD types chosen at creation, in the order chosen.
    dd_type_links: list["SessionDDType"] = Relationship(
        back_populates="session",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "SessionDDType.position",
        },
    )


class SessionDDType(SQLModel, table=True):
    """A DD type chosen for a session at its creation.

    A link, not a copy: a renamed DD type shows under its new name, and a DD
    type a session has chosen cannot be deleted (RESTRICT).
    """

    __tablename__ = "session_dd_types"

    session_id: int = Field(foreign_key="dd_sessions.id", ondelete="CASCADE", primary_key=True)
    dd_type_id: int = Field(
        foreign_key="dd_types.id", ondelete="RESTRICT", primary_key=True, index=True
    )
    position: int  # 0 for the first one chosen

    session: Optional["DDSession"] = Relationship(back_populates="dd_type_links")
    dd_type: Optional["DDType"] = Relationship()


class SessionCreate(SessionBase):
    # The DD types to run; none means every active type the user can see.
    dd_type_ids: list[int] | None = None


class SessionDDTypeRef(SQLModel):
    """A DD type of a session, as the API names it."""

    id: int
    code: str
    name: str


class SessionResponse(SessionBase):
    id: int
    session_code: str | None = None
    created_at: datetime
    updated_at: datetime
    created_by: int | None = None
    assigned_to: int | None = None
    created_by_username: str | None = None
    # The DD types chosen at creation, in their order, under their current name.
    dd_types: list[SessionDDTypeRef] = []
    # The company under review, as two entities (see models/company.py): the
    # fund itself and the company running it.
    company_name: str | None = None
    management_company_name: str | None = None

    @classmethod
    def of(cls, session: DDSession) -> "SessionResponse":
        """The session, with its DD types, its company's names and its
        creator's username."""
        response = cls.model_validate(session)
        response.dd_types = [
            SessionDDTypeRef(id=link.dd_type_id, code=link.dd_type.code, name=link.dd_type.name)
            for link in session.dd_type_links
            if link.dd_type is not None
        ]
        if session.company is not None:
            response.company_name = session.company.name
            response.management_company_name = session.company.management_company_name
        if session.creator is not None:
            response.created_by_username = session.creator.username or session.creator.email
        return response


class SessionStatusResponse(SQLModel):
    id: int
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
