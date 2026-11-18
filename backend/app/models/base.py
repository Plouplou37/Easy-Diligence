"""What every model shares: the metadata naming convention and column helpers.

Models import SQLModel from here, so the naming convention is in place before
the first table is declared. Stable constraint names are what lets Alembic
alter or drop a constraint later without guessing the name the database chose.
"""

import enum
from typing import Any, cast

from sqlalchemy import JSON, DateTime, Enum, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import QueryableAttribute
from sqlmodel import Field, SQLModel

SQLModel.metadata.naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# JSONB on PostgreSQL (indexable, compact), plain JSON elsewhere (SQLite tests).
JSONType = JSON().with_variant(JSONB(), "postgresql")

TIMESTAMP = DateTime(timezone=True)


def timestamp_field(*, created: bool = True, updated: bool = False, nullable: bool = True) -> Any:
    """A timezone-aware timestamp column filled by the database.

    created: defaults to now() on insert; updated: set to now() on every update.
    """
    column_kwargs: dict[str, Any] = {}
    if created:
        column_kwargs["server_default"] = func.now()
    if updated:
        column_kwargs["onupdate"] = func.now()
    return Field(default=None, sa_type=TIMESTAMP, sa_column_kwargs=column_kwargs, nullable=nullable)


def enum_type(enum_cls: type[enum.Enum], name: str, *, store_values: bool = False) -> Enum:
    """An enum stored as text with a CHECK constraint, not as a native ENUM type:
    adding a member then only needs the constraint replaced, not ALTER TYPE.

    By default the member NAMES are stored (SQLAlchemy's default, kept as the
    existing data used it); store_values stores the member values instead.
    """
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=50,
        values_callable=(lambda members: [m.value for m in members]) if store_values else None,
    )


def relation(attribute: Any) -> QueryableAttribute[Any]:
    """A relationship attribute, as loader options (joinedload) expect it.

    SQLModel types `DDSession.company` as the related model, not as the
    attribute SQLAlchemy sees at run time: this restores the right type.
    """
    return cast(QueryableAttribute[Any], attribute)


def stored_id(row: Any) -> int:
    """The id of a stored row. Typed optional on the models (None until the
    insert); once a row is read from or written to the database, it is set."""
    if row.id is None:
        raise ValueError(f"{type(row).__name__} has not been stored yet")
    return int(row.id)


__all__ = [
    "JSONType",
    "TIMESTAMP",
    "SQLModel",
    "enum_type",
    "relation",
    "stored_id",
    "timestamp_field",
]
