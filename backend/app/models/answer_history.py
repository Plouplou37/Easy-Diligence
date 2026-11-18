"""The versions of an answer: the table, and what the API returns."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from pydantic import field_validator
from sqlalchemy import Index, Text
from sqlmodel import Field, Relationship

from app.models.answer import decode_sources
from app.models.base import JSONType, SQLModel, timestamp_field

if TYPE_CHECKING:
    from app.models.answer import DDAnswer
    from app.models.user import User


class DDAnswerHistory(SQLModel, table=True):
    __tablename__ = "dd_answer_history"
    __table_args__ = (Index("ix_dd_answer_history_answer_version", "answer_id", "version"),)

    id: int | None = Field(default=None, primary_key=True)
    answer_id: int = Field(foreign_key="dd_answers.id", ondelete="CASCADE")
    version: int
    content: str = Field(sa_type=Text)
    sources: Any | None = Field(default=None, sa_type=JSONType)
    edited_by: int | None = Field(default=None, foreign_key="users.id")
    edit_reason: str | None = Field(default=None, sa_type=Text)
    created_at: datetime | None = timestamp_field()

    answer: Optional["DDAnswer"] = Relationship(back_populates="history")
    editor: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "DDAnswerHistory.edited_by"}
    )


class AnswerHistoryResponse(SQLModel):
    id: int
    answer_id: int
    version: int
    content: str
    sources: Any | None = None
    edited_by: int | None
    edit_reason: str | None
    created_at: datetime
    editor_name: str | None = None

    @field_validator("sources", mode="before")
    @classmethod
    def _sources(cls, value: Any) -> Any:
        return decode_sources(value)


class AnswerVersionHistory(SQLModel):
    """Every version of an answer, newest first."""

    answer_id: int
    current_version: int
    versions: list[AnswerHistoryResponse]
    total_versions: int
