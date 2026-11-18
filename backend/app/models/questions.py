"""The structure of a DD type: its sections and questions, the tables and what
the API reads and returns."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, Index, Text
from sqlmodel import Field, Relationship

from app.models.base import SQLModel, timestamp_field

if TYPE_CHECKING:
    from app.models.dd_types import DDType


# --- Sections ---------------------------------------------------------------------


class SectionBase(SQLModel):
    title: str = Field(max_length=255)
    # Theme context, sent to the model under the section title.
    description: str | None = Field(default=None, sa_type=Text)


class DDSection(SectionBase, table=True):
    __tablename__ = "dd_sections"
    __table_args__ = (
        Index("ix_dd_sections_dd_type_order", "dd_type_id", "order_index"),
        CheckConstraint("order_index >= 0", name="order_non_negative"),
    )

    id: int | None = Field(default=None, primary_key=True)
    dd_type_id: int = Field(foreign_key="dd_types.id")
    section_code: str = Field(max_length=50)  # A, B... (services/question_codes.py)
    order_index: int = Field(default=0)
    created_at: datetime | None = timestamp_field()

    dd_type_obj: Optional["DDType"] = Relationship(back_populates="sections")
    questions: list["DDQuestion"] = Relationship(
        back_populates="section",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "DDQuestion.order_index, DDQuestion.id",
        },
    )


class SectionCreate(SectionBase):
    """A new section; without an order, it goes after the last one."""

    order_index: int | None = Field(default=None, ge=0)


class SectionUpdate(SQLModel):
    section_code: str | None = Field(default=None, max_length=50)
    title: str | None = Field(default=None, max_length=255)
    description: str | None = None
    order_index: int | None = Field(default=None, ge=0)


# --- Questions --------------------------------------------------------------------


class QuestionBase(SQLModel):
    question_text: str = Field(sa_type=Text)
    # "Where to look": the sources to consult, sent to the model.
    context_prompt: str | None = Field(default=None, sa_type=Text)
    order_index: int = Field(default=0, ge=0)


class DDQuestion(QuestionBase, table=True):
    __tablename__ = "dd_questions"
    __table_args__ = (
        Index("ix_dd_questions_section_order", "section_id", "order_index"),
        CheckConstraint("order_index >= 0", name="order_non_negative"),
    )

    id: int | None = Field(default=None, primary_key=True)
    section_id: int = Field(foreign_key="dd_sections.id")
    question_code: str = Field(max_length=50)  # A.01... (services/question_codes.py)
    created_at: datetime | None = timestamp_field()

    section: Optional["DDSection"] = Relationship(back_populates="questions")


class QuestionCreate(QuestionBase):
    """A new question; without a code, it takes the next one of its section."""

    question_code: str | None = Field(default=None, max_length=50)


class QuestionUpdate(SQLModel):
    question_code: str | None = Field(default=None, max_length=50)
    question_text: str | None = None
    context_prompt: str | None = None
    order_index: int | None = Field(default=None, ge=0)


class ReorderRequest(SQLModel):
    new_order: int = Field(ge=0)


# --- Read back ----------------------------------------------------------------------


class QuestionResponse(QuestionBase):
    id: int
    question_code: str


class SectionResponse(SectionBase):
    id: int
    section_code: str
    order_index: int
    questions: list[QuestionResponse]


class DDTypeDetailResponse(SQLModel):
    """A DD type with its whole structure."""

    code: str
    name: str
    description: str | None
    icon: str | None
    is_active: bool
    is_validated: bool
    sections: list[SectionResponse] = []
