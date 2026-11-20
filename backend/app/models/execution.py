import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Index, UniqueConstraint
from sqlmodel import Field, Relationship

from app.models.base import SQLModel, defaulted_field, enum_type, timestamp_field

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
    """The run of one DD type within a session: one per (session, DD type),
    started once, then resumed (services/processing.py)."""

    __tablename__ = "dd_executions"
    __table_args__ = (
        Index("ix_dd_executions_session_status", "session_id", "status"),
        UniqueConstraint("session_id", "dd_type_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="dd_sessions.id", ondelete="CASCADE")
    dd_type_id: int = Field(foreign_key="dd_types.id", ondelete="RESTRICT", index=True)
    status: ExecutionStatus = defaulted_field(
        ExecutionStatus.NOT_STARTED,
        sa_type=enum_type(ExecutionStatus, "execution_status", store_values=True),
    )
    conversation_id: str | None = Field(default=None, max_length=255, unique=True)
    validator_id: int | None = Field(default=None, foreign_key="users.id")
    created_at: datetime = timestamp_field(nullable=False)
    updated_at: datetime = timestamp_field(updated=True, nullable=False)

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
