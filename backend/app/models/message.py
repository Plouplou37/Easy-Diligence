from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Text, UniqueConstraint
from sqlmodel import Field, Relationship

from app.models.base import JSONType, SQLModel, timestamp_field

if TYPE_CHECKING:
    from app.models.response import DDResponse


class DDMessage(SQLModel, table=True):
    __tablename__ = "dd_messages"
    # One message per index within a response (also serves lookups by response).
    __table_args__ = (
        UniqueConstraint("response_id", "message_index", name="uq_message_response_index"),
    )

    id: int | None = Field(default=None, primary_key=True)
    response_id: str = Field(
        max_length=255, foreign_key="dd_responses.response_id", ondelete="CASCADE"
    )
    message_index: int
    role: str = Field(max_length=50)
    content: str | None = Field(default=None, sa_type=Text)
    tool_calls: Any | None = Field(default=None, sa_type=JSONType)
    openai_message_id: str | None = Field(default=None, max_length=255, index=True)
    created_at: datetime | None = timestamp_field()

    response: Optional["DDResponse"] = Relationship(back_populates="messages")
