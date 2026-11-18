"""Shared authorization helpers for per-user data isolation.

Centralizes the ownership/visibility rules used across the API so the same
pattern is not duplicated in every router:

- Sessions (and everything hanging off a session: answers, executions) are
  visible to their creator/assignee. Admins see everything.
- DD types are private to their owner (``created_by``); system types
  (``is_system``) and legacy types with no owner (``created_by IS NULL``) are
  shared and visible to everyone. Admins see everything.
- Companies (Asset Manager / Fund) are private to their creator
  (``created_by``); legacy companies with no owner (``created_by IS NULL``) are
  shared and visible to everyone. Admins see everything.
"""

from fastapi import HTTPException, status
from sqlalchemy import or_

from app.models.company import Company
from app.models.dd_types import DDType
from app.models.session import DDSession
from app.models.user import User


def user_is_admin(user: User) -> bool:
    """Return True if the user has the admin role (sees all data)."""
    return getattr(user, "role", None) == "admin"


# --- Sessions (and session-scoped resources) -------------------------------

def filter_sessions_for_user(query, user: User):
    """Restrict a DDSession query to sessions the user may see.

    Admins are unrestricted. Other users see sessions they created or were
    assigned to. The query must select/filter on the DDSession table.
    """
    if user_is_admin(user):
        return query
    return query.filter(
        or_(
            DDSession.created_by == user.id,
            DDSession.assigned_to == user.id,
        )
    )


def user_can_access_session(session: DDSession, user: User) -> bool:
    """Whether the user may access a single session."""
    if user_is_admin(user):
        return True
    return session.created_by == user.id or session.assigned_to == user.id


def assert_session_access(session: DDSession, user: User) -> None:
    """Raise 403 if the user cannot access the given session."""
    if not user_can_access_session(session, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this session",
        )


# --- DD types --------------------------------------------------------------

def filter_dd_types_for_user(query, user: User):
    """Restrict a DDType query to types the user may see.

    Admins are unrestricted. Other users see system/shared types
    (is_system OR created_by IS NULL) plus types they own.
    """
    if user_is_admin(user):
        return query
    return query.filter(
        or_(
            DDType.is_system == True,  # noqa: E712 - SQLAlchemy needs ==
            DDType.created_by == None,  # noqa: E711 - shared/legacy types
            DDType.created_by == user.id,
        )
    )


def user_can_view_dd_type(dd_type: DDType, user: User) -> bool:
    """Whether the user may view a single DD type."""
    if user_is_admin(user):
        return True
    return (
        bool(dd_type.is_system)
        or dd_type.created_by is None
        or dd_type.created_by == user.id
    )


def assert_dd_type_view(dd_type: DDType, user: User) -> None:
    """Raise 404 if the user cannot even see the given DD type.

    404 (not 403) so private types are not enumerable by other users.
    """
    if not user_can_view_dd_type(dd_type, user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DD type not found",
        )


def user_can_modify_dd_type(dd_type: DDType, user: User) -> bool:
    """Whether the user may modify/delete a single DD type.

    Only the owner (or an admin) may modify. Shared system types are not
    owned by regular users, so they cannot be modified by them.
    """
    if user_is_admin(user):
        return True
    return dd_type.created_by is not None and dd_type.created_by == user.id


def assert_dd_type_ownership(dd_type: DDType, user: User) -> None:
    """Raise 403 if the user may not modify the given DD type."""
    if not user_can_modify_dd_type(dd_type, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to modify this DD type",
        )


# --- Companies (Asset Manager / Fund) --------------------------------------

def filter_companies_for_user(query, user: User):
    """Restrict a Company query to companies the user may see.

    Admins are unrestricted. Other users see companies they created plus legacy
    shared companies with no owner (created_by IS NULL).
    """
    if user_is_admin(user):
        return query
    return query.filter(
        or_(
            Company.created_by == None,  # noqa: E711 - shared/legacy companies
            Company.created_by == user.id,
        )
    )


def user_can_view_company(company: Company, user: User) -> bool:
    """Whether the user may view a single company."""
    if user_is_admin(user):
        return True
    return company.created_by is None or company.created_by == user.id


def assert_company_view(company: Company, user: User) -> None:
    """Raise 404 if the user cannot see the given company.

    404 (not 403) so other users' companies are not enumerable.
    """
    if not user_can_view_company(company, user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )


def user_can_modify_company(company: Company, user: User) -> bool:
    """Whether the user may modify a single company.

    Only the owner (or an admin) may modify. Shared/legacy companies with no
    owner can only be modified by an admin.
    """
    if user_is_admin(user):
        return True
    return company.created_by is not None and company.created_by == user.id


def assert_company_ownership(company: Company, user: User) -> None:
    """Raise 403 if the user may not modify the given company."""
    if not user_can_modify_company(company, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to modify this company",
        )
