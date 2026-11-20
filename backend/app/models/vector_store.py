from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Index, Text, UniqueConstraint, text
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
    created_at: datetime = timestamp_field(nullable=False)
    updated_at: datetime | None = timestamp_field(updated=True)

    creator: Optional["User"] = Relationship()
    session_assignments: list["SessionVectorStore"] = Relationship(back_populates="vector_store")


class SessionVectorStore(SQLModel, table=True):
    """A vector store assigned to a session: to one DD type, or to the whole
    session when dd_type_id is NULL."""

    __tablename__ = "session_vector_stores"
    __table_args__ = (
        UniqueConstraint("session_id", "dd_type_id", "vector_store_id"),
        # The constraint above lets a store be assigned twice to the whole
        # session: two NULL dd_type_id are distinct to SQL. Partial index rather
        # than NULLS NOT DISTINCT, as for dd_summaries (models/summary.py).
        Index(
            "ix_session_vector_stores_one_session_wide",
            "session_id",
            "vector_store_id",
            unique=True,
            postgresql_where=text("dd_type_id IS NULL"),
            sqlite_where=text("dd_type_id IS NULL"),
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="dd_sessions.id", ondelete="CASCADE", index=True)
    # NULL = whole session
    dd_type_id: int | None = Field(
        default=None, foreign_key="dd_types.id", ondelete="CASCADE", index=True
    )
    vector_store_id: str = Field(max_length=255, foreign_key="vector_stores.id", index=True)
    assigned_at: datetime = timestamp_field(nullable=False)
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
