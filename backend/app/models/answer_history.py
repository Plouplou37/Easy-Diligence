from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Index, Text
from sqlmodel import Field, Relationship

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
