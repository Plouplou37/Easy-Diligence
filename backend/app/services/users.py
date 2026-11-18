"""Managing the accounts (admins only): listing, role, activation, deletion."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlmodel import col

from app.core.exceptions import ConflictError, InvalidRequestError, NotFoundError
from app.models.answer import DDAnswer
from app.models.answer_history import DDAnswerHistory
from app.models.company import Company
from app.models.dd_types import DDType
from app.models.execution import DDExecution
from app.models.session import DDSession
from app.models.summary import DDSummary, DDSummaryBatch
from app.models.user import User
from app.models.vector_store import SessionVectorStore, VectorStore
from app.schemas.user import Role

_OWNS_DATA = "This user owns sessions or other data: deactivate the account instead."


def _get(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found")
    return user


def list_users(
    db: Session, page: int, per_page: int, search: str | None = None
) -> tuple[list[User], int]:
    """A page of the accounts, matching `search` (name, e-mail or username) if
    given, with the number of matching accounts."""
    query = db.query(User)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                col(User.full_name).ilike(term),
                col(User.email).ilike(term),
                col(User.username).ilike(term),
            )
        )
    total = query.count()
    users = query.order_by(col(User.id)).offset((page - 1) * per_page).limit(per_page).all()
    return users, total


def set_role(db: Session, admin: User, user_id: int, role: Role) -> User:
    if user_id == admin.id and role != "admin":
        raise InvalidRequestError("Cannot remove admin role from yourself")
    user = _get(db, user_id)
    user.role = role
    user.updated_at = datetime.now(UTC)
    db.commit()
    return user


def set_active(db: Session, admin: User, user_id: int, active: bool) -> User:
    if user_id == admin.id and not active:
        raise InvalidRequestError("Cannot deactivate yourself")
    user = _get(db, user_id)
    user.is_active = active
    user.updated_at = datetime.now(UTC)
    db.commit()
    return user


def _owns_data(db: Session, user_id: int) -> bool:
    """Whether anything in the database points at the account."""
    pointers: list[Any] = [
        DDSession.created_by,
        DDSession.assigned_to,
        Company.created_by,
        Company.updated_by,
        DDType.created_by,
        VectorStore.created_by,
        SessionVectorStore.assigned_by,
        DDAnswer.edited_by,
        DDAnswerHistory.edited_by,
        DDSummary.edited_by,
        DDSummaryBatch.created_by,
        DDExecution.validator_id,
    ]
    return any(
        db.query(column).filter(col(column) == user_id).first() is not None for column in pointers
    )


def delete_user(db: Session, admin: User, user_id: int) -> str:
    """Delete an account that owns nothing; returns the name it went by.

    An account that created or was assigned sessions, created companies, DD
    types or vector stores, or edited answers, cannot go: deleting it would
    blank those links, and a company with no creator is shared with everyone.
    Deactivate it instead.
    """
    if user_id == admin.id:
        raise InvalidRequestError("Cannot delete yourself")
    user = _get(db, user_id)
    if user.role == "admin":
        raise InvalidRequestError("Cannot delete admin users")
    if _owns_data(db, user_id):
        raise ConflictError(_OWNS_DATA)
    name = user.full_name or user.username
    try:
        db.delete(user)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError(_OWNS_DATA) from None
    return name
