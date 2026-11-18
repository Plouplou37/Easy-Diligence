"""Companies under review: the table, and what the API reads and returns."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Text
from sqlmodel import Field, Relationship

from app.models.base import SQLModel, timestamp_field

if TYPE_CHECKING:
    from app.models.session import DDSession
    from app.models.user import User


class CompanyBase(SQLModel):
    # The DD subject: the fund / product under review.
    name: str = Field(max_length=255, index=True)
    website_url: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, sa_type=Text)
    # The company running that fund. Kept apart from `name` so the engine can
    # tell the model which entity a question is about instead of guessing --
    # web search quality depends on it. NULL when unknown.
    management_company_name: str | None = Field(default=None, max_length=255)
    management_company_website: str | None = Field(default=None, max_length=500)


class Company(CompanyBase, table=True):
    __tablename__ = "companies"

    id: int | None = Field(default=None, primary_key=True)
    created_by: int | None = Field(default=None, foreign_key="users.id", index=True)
    updated_by: int | None = Field(default=None, foreign_key="users.id", index=True)
    created_at: datetime | None = timestamp_field(nullable=False)
    updated_at: datetime | None = timestamp_field(updated=True, nullable=False)

    sessions: list["DDSession"] = Relationship(back_populates="company")
    creator: Optional["User"] = Relationship(
        back_populates="companies_created",
        sa_relationship_kwargs={"foreign_keys": "Company.created_by"},
    )
    updater: Optional["User"] = Relationship(
        back_populates="companies_updated",
        sa_relationship_kwargs={"foreign_keys": "Company.updated_by"},
    )


class CompanyCreate(CompanyBase):
    """A new company, or the full replacement of one."""


class CompanyResponse(CompanyBase):
    id: int
    created_at: datetime
    updated_at: datetime
