import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Index
from sqlmodel import Field, Relationship

from app.models.base import SQLModel, timestamp_field

if TYPE_CHECKING:
    from app.models.answer import DDAnswer
    from app.models.dd_types import DDType
    from app.models.response import DDResponse
    from app.models.session import DDSession
    from app.models.user import User


class ExecutionStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    GENERATED = "generated"
    FAILED = "failed"
    PAUSED = "paused"
    UNDER_REVIEW = "under_review"
    VALIDATED = "validated"
    FINALIZED = "finalized"


class DDExecution(SQLModel, table=True):
    """One run of one DD type within a session."""

    __tablename__ = "dd_executions"
    __table_args__ = (Index("ix_dd_executions_session_status", "session_id", "status"),)

    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="dd_sessions.id", ondelete="CASCADE")
    dd_type_id: int = Field(foreign_key="dd_types.id", ondelete="RESTRICT", index=True)
    # Plain text holding an ExecutionStatus value.
    status: str | None = Field(default=ExecutionStatus.NOT_STARTED.value, max_length=50)
    conversation_id: str | None = Field(default=None, max_length=255, unique=True)
    validator_id: int | None = Field(default=None, foreign_key="users.id")
    created_at: datetime | None = timestamp_field()
    updated_at: datetime | None = timestamp_field(updated=True)

    session: Optional["DDSession"] = Relationship(back_populates="executions")
    dd_type: Optional["DDType"] = Relationship(back_populates="executions")
    validator: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "DDExecution.validator_id"}
    )
    responses: list["DDResponse"] = Relationship(
        back_populates="execution", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    answers: list["DDAnswer"] = Relationship(
        back_populates="execution", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
