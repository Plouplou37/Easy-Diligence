from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, Index, Text
from sqlmodel import Field, Relationship

from app.models.base import SQLModel, timestamp_field

if TYPE_CHECKING:
    from app.models.dd_types import DDType


class DDSection(SQLModel, table=True):
    __tablename__ = "dd_sections"
    __table_args__ = (
        Index("ix_dd_sections_dd_type_order", "dd_type_id", "order_index"),
        CheckConstraint("order_index >= 0", name="order_non_negative"),
    )

    id: int | None = Field(default=None, primary_key=True)
    dd_type_id: int = Field(foreign_key="dd_types.id")
    section_code: str = Field(max_length=50)
    title: str = Field(max_length=255)
    # Theme context, sent to the model under the section title.
    description: str | None = Field(default=None, sa_type=Text)
    order_index: int = Field(default=0)
    created_at: datetime | None = timestamp_field()

    dd_type_obj: Optional["DDType"] = Relationship(back_populates="sections")
    questions: list["DDQuestion"] = Relationship(
        back_populates="section", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class DDQuestion(SQLModel, table=True):
    __tablename__ = "dd_questions"
    __table_args__ = (
        Index("ix_dd_questions_section_order", "section_id", "order_index"),
        CheckConstraint("order_index >= 0", name="order_non_negative"),
    )

    id: int | None = Field(default=None, primary_key=True)
    section_id: int = Field(foreign_key="dd_sections.id")
    question_code: str = Field(max_length=50)
    question_text: str = Field(sa_type=Text)
    # "Where to look": the sources to consult, sent to the model.
    context_prompt: str | None = Field(default=None, sa_type=Text)
    order_index: int = Field(default=0)
    created_at: datetime | None = timestamp_field()

    section: Optional["DDSection"] = Relationship(back_populates="questions")
