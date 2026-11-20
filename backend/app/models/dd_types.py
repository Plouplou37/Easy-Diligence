"""DD types (questionnaires): the table, and what the API reads and returns."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Text
from sqlmodel import Field, Relationship

from app.models.base import SQLModel, defaulted_field, timestamp_field

if TYPE_CHECKING:
    from app.models.execution import DDExecution
    from app.models.questions import DDSection
    from app.models.user import User

# Shown on the DD card. The import used to default to the literal string
# "[DD]", which is truthy and so slipped past the frontend's own emoji
# fallback: the card rendered the four characters in place of an icon.
DEFAULT_DD_TYPE_ICON = "📋"


class DDTypeBase(SQLModel):
    code: str = Field(max_length=50, unique=True, index=True)
    name: str = Field(max_length=255)
    description: str | None = Field(default=None, sa_type=Text)
    icon: str | None = Field(default=None, max_length=10)  # emoji or icon reference
    order_index: int = defaulted_field(0)


class DDType(DDTypeBase, table=True):
    __tablename__ = "dd_types"

    id: int | None = Field(default=None, primary_key=True)
    is_active: bool = defaulted_field(True)
    is_system: bool = defaulted_field(False)  # system types can't be deleted
    is_validated: bool = defaulted_field(False)  # validation freezes the structure
    # Owner of this DD type. NULL = shared (system templates visible to everyone).
    created_by: int | None = Field(default=None, foreign_key="users.id", index=True)
    created_at: datetime = timestamp_field(nullable=False)
    updated_at: datetime = timestamp_field(updated=True, nullable=False)

    sections: list["DDSection"] = Relationship(
        back_populates="dd_type_obj",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "DDSection.order_index, DDSection.id",
        },
    )
    executions: list["DDExecution"] = Relationship(back_populates="dd_type")
    creator: Optional["User"] = Relationship()


class DDTypeCreate(DDTypeBase):
    """A new, empty DD type."""


class DDTypeUpdate(SQLModel):
    """What may change on a DD type; fields left out stay as they are."""

    code: str | None = Field(default=None, max_length=50)
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    icon: str | None = Field(default=None, max_length=10)
    is_active: bool | None = None
    order_index: int | None = None


class DDTypeResponse(DDTypeBase):
    id: int
    is_active: bool
    is_system: bool
    is_validated: bool
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime
