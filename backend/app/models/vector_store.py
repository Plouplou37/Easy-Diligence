from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Text
from sqlmodel import Field, Relationship

from app.models.base import SQLModel, timestamp_field

if TYPE_CHECKING:
    from app.models.session import DDSession
    from app.models.user import User


class VectorStore(SQLModel, table=True):
    """An OpenAI vector store we track. Only ownership and our own fields live
    here; everything else is read from OpenAI."""

    __tablename__ = "vector_stores"

    id: str = Field(primary_key=True, max_length=255)  # OpenAI vector store ID
    name: str = Field(max_length=255)
    description: str | None = Field(default=None, sa_type=Text)  # ours, not OpenAI's
    created_by: int = Field(foreign_key="users.id", index=True)  # owner
    created_at: datetime | None = timestamp_field()
    updated_at: datetime | None = timestamp_field(updated=True)

    creator: Optional["User"] = Relationship()
    session_assignments: list["SessionVectorStore"] = Relationship(back_populates="vector_store")


class SessionVectorStore(SQLModel, table=True):
    """A vector store assigned to a session: to one DD type, or to the whole
    session when dd_type_id is NULL."""

    __tablename__ = "session_vector_stores"

    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="dd_sessions.id", ondelete="CASCADE", index=True)
    dd_type_id: int | None = Field(default=None)  # NULL = whole session
    vector_store_id: str = Field(max_length=255, foreign_key="vector_stores.id", index=True)
    assigned_at: datetime | None = timestamp_field()
    assigned_by: int = Field(foreign_key="users.id")

    session: Optional["DDSession"] = Relationship()
    vector_store: Optional["VectorStore"] = Relationship(back_populates="session_assignments")
    assignee: Optional["User"] = Relationship()
