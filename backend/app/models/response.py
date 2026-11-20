from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlmodel import Field, Relationship

from app.models.base import JSONType, SQLModel, timestamp_field

if TYPE_CHECKING:
    from app.models.execution import DDExecution
    from app.models.message import DDMessage


class DDResponse(SQLModel, table=True):
    """A raw OpenAI response, chained to the previous one of the same run."""

    __tablename__ = "dd_responses"

    id: int | None = Field(default=None, primary_key=True)
    execution_id: int = Field(foreign_key="dd_executions.id", ondelete="CASCADE", index=True)
    response_id: str = Field(max_length=255, unique=True)
    previous_response_id: str | None = Field(
        default=None, max_length=255, foreign_key="dd_responses.response_id", index=True
    )
    openai_response: Any = Field(sa_type=JSONType, nullable=False)
    created_at: datetime = timestamp_field(nullable=False)

    execution: Optional["DDExecution"] = Relationship(back_populates="responses")
    previous_response: Optional["DDResponse"] = Relationship(
        back_populates="next_responses",
        sa_relationship_kwargs={"remote_side": "DDResponse.response_id"},
    )
    next_responses: list["DDResponse"] = Relationship(back_populates="previous_response")
    messages: list["DDMessage"] = Relationship(
        back_populates="response", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
