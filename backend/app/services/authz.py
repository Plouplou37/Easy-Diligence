"""Who may see and change what: the per-user isolation rules, in one place.

- Sessions (and everything hanging off a session: answers, executions) are
  visible to their creator and their assignee.
- DD types are private to their owner (``created_by``); system types
  (``is_system``) and legacy types with no owner (``created_by IS NULL``) are
  shared with everyone.
- Companies are private to their creator; legacy companies with no owner are
  shared with everyone.
- Admins see and change everything.

The ``assert_*`` functions raise the business errors of core/exceptions.py
(404 where existence itself must not leak, 403 otherwise).
"""

from typing import Any

from sqlalchemy import or_
from sqlmodel import col

from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.models.company import Company
from app.models.dd_types import DDType
from app.models.session import DDSession
from app.models.user import User


def user_is_admin(user: User) -> bool:
    """Return True if the user has the admin role (sees all data)."""
    return getattr(user, "role", None) == "admin"


# --- Sessions (and session-scoped resources) -------------------------------


def filter_sessions_for_user(query: Any, user: User) -> Any:
    """Restrict a query that involves the DDSession table to the user's sessions."""
    if user_is_admin(user):
        return query
    return query.filter(
        or_(col(DDSession.created_by) == user.id, col(DDSession.assigned_to) == user.id)
    )


def user_can_access_session(session: DDSession, user: User) -> bool:
    """Whether the user may access a single session."""
    if user_is_admin(user):
        return True
    return session.created_by == user.id or session.assigned_to == user.id


def assert_session_access(session: DDSession, user: User) -> None:
    """Refuse (403) a user who cannot access the session."""
    if not user_can_access_session(session, user):
        raise PermissionDeniedError("You don't have permission to access this session")


# --- DD types --------------------------------------------------------------


def filter_dd_types_for_user(query: Any, user: User) -> Any:
    """Restrict a DDType query to the types the user may see."""
    if user_is_admin(user):
        return query
    return query.filter(
        or_(
            col(DDType.is_system).is_(True),
            col(DDType.created_by).is_(None),
            col(DDType.created_by) == user.id,
        )
    )


def user_can_view_dd_type(dd_type: DDType, user: User) -> bool:
    """Whether the user may view a single DD type."""
    if user_is_admin(user):
        return True
    return bool(dd_type.is_system) or dd_type.created_by is None or dd_type.created_by == user.id


def assert_dd_type_view(dd_type: DDType, user: User) -> None:
    """404 for a DD type the user cannot see, so private types are not enumerable."""
    if not user_can_view_dd_type(dd_type, user):
        raise NotFoundError("DD type not found")


def user_can_modify_dd_type(dd_type: DDType, user: User) -> bool:
    """Only the owner (or an admin) may modify; shared types have no owner."""
    if user_is_admin(user):
        return True
    return dd_type.created_by is not None and dd_type.created_by == user.id


def assert_dd_type_ownership(dd_type: DDType, user: User) -> None:
    """Refuse (403) a user who may not modify the DD type."""
    if not user_can_modify_dd_type(dd_type, user):
        raise PermissionDeniedError("You don't have permission to modify this DD type")


# --- Companies -------------------------------------------------------------


def filter_companies_for_user(query: Any, user: User) -> Any:
    """Restrict a Company query to the companies the user may see."""
    if user_is_admin(user):
        return query
    return query.filter(or_(col(Company.created_by).is_(None), col(Company.created_by) == user.id))


def user_can_view_company(company: Company, user: User) -> bool:
    """Whether the user may view a single company."""
    if user_is_admin(user):
        return True
    return company.created_by is None or company.created_by == user.id


def assert_company_view(company: Company, user: User) -> None:
    """404 for a company the user cannot see, so others' companies are not enumerable."""
    if not user_can_view_company(company, user):
        raise NotFoundError("Company not found")


def user_can_modify_company(company: Company, user: User) -> bool:
    """Only the owner (or an admin) may modify; shared companies only by an admin."""
    if user_is_admin(user):
        return True
    return company.created_by is not None and company.created_by == user.id


def assert_company_ownership(company: Company, user: User) -> None:
    """Refuse (403) a user who may not modify the company."""
    if not user_can_modify_company(company, user):
        raise PermissionDeniedError("You don't have permission to modify this company")
