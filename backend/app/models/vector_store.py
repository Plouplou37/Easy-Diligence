from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Text
from sqlmodel import Field, Relationship

from app.models.base import SQLModel, timestamp_field

if TYPE_CHECKING:
    from app.models.session import DDSession
    from app.models.user import User


class VectorStoreBase(SQLModel):
    name: str = Field(max_length=255)
    description: str | None = Field(default=None, sa_type=Text)  # ours, not OpenAI's


class VectorStore(VectorStoreBase, table=True):
    """An OpenAI vector store we track. Only ownership and our own fields live
    here; everything else is read from OpenAI."""

    __tablename__ = "vector_stores"

    id: str = Field(primary_key=True, max_length=255)  # OpenAI vector store ID
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


class VectorStoreCreate(VectorStoreBase):
    # Days without use before OpenAI deletes the store.
    expires_after_days: int = Field(default=30, ge=1, le=365)


class VectorStoreUpdate(SQLModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None


class VectorStoreResponse(VectorStoreBase):
    """A store, with its state at OpenAI ("expired" or "missing" once gone there)."""

    id: str
    file_count: int
    total_bytes: int
    status: str
    expires_after_days: int | None = None
    expires_at: datetime | None = None
    last_active_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SessionVectorStoreAssignment(SQLModel):
    """Body of an assignment: a DD type, or nothing for the whole session."""

    dd_type_id: int | None = None
