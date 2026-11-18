"""Account management, for admins."""

import math

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.admin import (
    AdminActionResponse,
    UserListItem,
    UserListResponse,
    UserRoleUpdate,
    UserStatusUpdate,
)
from app.services import users

router = APIRouter()


@router.get("/users", response_model=UserListResponse)
def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    search: str | None = Query(None, description="Search users by name, email, or username"),
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """A page of the accounts, optionally searched."""
    found, total = users.list_users(db, page, per_page, search)
    return UserListResponse(
        users=[UserListItem.model_validate(user) for user in found],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=math.ceil(total / per_page),
    )


@router.put("/users/{user_id}/role", response_model=AdminActionResponse)
def update_user_role(
    user_id: int,
    data: UserRoleUpdate,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Make an account an admin or an analyst. An admin cannot demote themselves."""
    users.set_role(db, admin, user_id, data.role)
    return AdminActionResponse(
        success=True, message=f"User role updated to {data.role}", user_id=user_id
    )


@router.put("/users/{user_id}/status", response_model=AdminActionResponse)
def update_user_status(
    user_id: int,
    data: UserStatusUpdate,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Activate or deactivate an account. An admin cannot deactivate themselves."""
    users.set_active(db, admin, user_id, data.is_active)
    action = "activated" if data.is_active else "deactivated"
    return AdminActionResponse(success=True, message=f"User {action} successfully", user_id=user_id)


@router.delete("/users/{user_id}", response_model=AdminActionResponse)
def delete_user(
    user_id: int,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Delete an account that owns nothing (deactivate the others)."""
    name = users.delete_user(db, admin, user_id)
    return AdminActionResponse(
        success=True, message=f"User {name} deleted successfully", user_id=user_id
    )
