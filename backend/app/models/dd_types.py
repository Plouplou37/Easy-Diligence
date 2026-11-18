from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Text
from sqlmodel import Field, Relationship

from app.models.base import SQLModel, timestamp_field

if TYPE_CHECKING:
    from app.models.execution import DDExecution
    from app.models.questions import DDSection
    from app.models.user import User

# Shown on the DD card. The import used to default to the literal string
# "[DD]", which is truthy and so slipped past the frontend's own emoji
# fallback: the card rendered the four characters in place of an icon.
DEFAULT_DD_TYPE_ICON = "📋"


class DDType(SQLModel, table=True):
    __tablename__ = "dd_types"

    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(max_length=50, unique=True, index=True)
    name: str = Field(max_length=255)
    description: str | None = Field(default=None, sa_type=Text)
    icon: str | None = Field(default=None, max_length=10)  # emoji or icon reference
    is_active: bool | None = Field(default=True)
    is_system: bool | None = Field(default=False)  # system types can't be deleted
    is_validated: bool | None = Field(default=False)  # validation freezes the structure
    order_index: int | None = Field(default=0)
    # Owner of this DD type. NULL = shared (system templates visible to everyone).
    created_by: int | None = Field(default=None, foreign_key="users.id", index=True)
    created_at: datetime | None = timestamp_field()
    updated_at: datetime | None = timestamp_field(updated=True)

    sections: list["DDSection"] = Relationship(
        back_populates="dd_type_obj", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    executions: list["DDExecution"] = Relationship(back_populates="dd_type")
    creator: Optional["User"] = Relationship()
