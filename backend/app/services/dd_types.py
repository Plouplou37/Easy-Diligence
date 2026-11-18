"""DD types: lookups shared by the routes and the services."""

from sqlalchemy.orm import Session
from sqlmodel import col

from app.core.exceptions import NotFoundError
from app.models.dd_types import DDType
from app.models.user import User
from app.services.authz import assert_dd_type_view


def get_dd_type_by_code(db: Session, code: str, user: User | None = None) -> DDType:
    """The DD type with this code. With a user, one they may see: a private
    type of someone else is reported missing, like an unknown code."""
    dd_type = db.query(DDType).filter(col(DDType.code) == code).first()
    if dd_type is None:
        raise NotFoundError(f"DD type with code '{code}' not found")
    if user is not None:
        assert_dd_type_view(dd_type, user)
    return dd_type
