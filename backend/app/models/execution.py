import enum
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Index, UniqueConstraint
from sqlmodel import Field, Relationship

from app.models.base import TIMESTAMP, SQLModel, defaulted_field, enum_type, timestamp_field

if TYPE_CHECKING:
    from app.models.answer import DDAnswer
    from app.models.dd_types import DDType
    from app.models.response import DDResponse
    from app.models.session import DDSession


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
    # Time spent running, pauses left out. A start or a resume sets
    # running_since (services/processing.py); when the run stops (pause, end,
    # failure), the engine adds that stretch to run_seconds and clears it.
    run_seconds: int = defaulted_field(0)
    running_since: datetime | None = Field(default=None, sa_type=TIMESTAMP)
    created_at: datetime = timestamp_field(nullable=False)
    updated_at: datetime = timestamp_field(updated=True, nullable=False)

    session: Optional["DDSession"] = Relationship(back_populates="executions")
    dd_type: Optional["DDType"] = Relationship(back_populates="executions")
    responses: list["DDResponse"] = Relationship(
        back_populates="execution", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    answers: list["DDAnswer"] = Relationship(
        back_populates="execution", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    def elapsed_seconds(self) -> int:
        """Time spent running so far: the stretches already over, plus the
        one going on. A pause does not count."""
        total = self.run_seconds or 0
        if self.running_since is not None:
            since = self.running_since
            if since.tzinfo is None:  # SQLite (the tests) gives naive UTC times
                since = since.replace(tzinfo=UTC)
            total += max(0, int((datetime.now(UTC) - since).total_seconds()))
        return total
