from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Optional
import math

from app.database import get_db
from app.schemas.admin import (
    UserListResponse, UserListItem, UserRoleUpdate, 
    UserStatusUpdate, AdminActionResponse
)
from app.core.auth import (
    get_all_users, update_user_role, update_user_status, 
    is_admin, get_user
)
from app.core.security import verify_token

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_admin_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Dependency to verify admin user."""
    # Verify token
    payload = verify_token(token, token_type="access")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = int(payload.get("sub"))
    user = get_user(db, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not is_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return user

@router.get("/users", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search users by name, email, or username"),
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get paginated list of all users (admin only)."""
    skip = (page - 1) * per_page
    
    # Get users with pagination
    users, total = get_all_users(db, skip=skip, limit=per_page)
    
    # Apply search filter if provided
    if search:
        search_lower = search.lower()
        filtered_users = []
        for user in users:
            if (search_lower in (user.full_name or "").lower() or
                search_lower in user.email.lower() or
                search_lower in user.username.lower()):
                filtered_users.append(user)
        users = filtered_users
        total = len(filtered_users)
    
    total_pages = math.ceil(total / per_page)
    
    # Convert to response format
    user_items = [UserListItem.from_orm(user) for user in users]
    
    return UserListResponse(
        users=user_items,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )

@router.put("/users/{user_id}/role", response_model=AdminActionResponse)
async def update_user_role_endpoint(
    user_id: int,
    role_update: UserRoleUpdate,
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update user role (admin only)."""
    # Validate role
    valid_roles = ["admin", "analyst"]
    if role_update.role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {valid_roles}"
        )
    
    # Prevent self-demotion
    if user_id == current_user.id and role_update.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove admin role from yourself"
        )
    
    # Update role
    success = update_user_role(db, user_id, role_update.role)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return AdminActionResponse(
        success=True,
        message=f"User role updated to {role_update.role}",
        user_id=user_id
    )

@router.put("/users/{user_id}/status", response_model=AdminActionResponse)
async def update_user_status_endpoint(
    user_id: int,
    status_update: UserStatusUpdate,
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update user active status (admin only)."""
    # Prevent self-deactivation
    if user_id == current_user.id and not status_update.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate yourself"
        )
    
    # Update status
    success = update_user_status(db, user_id, status_update.is_active)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    action = "activated" if status_update.is_active else "deactivated"
    return AdminActionResponse(
        success=True,
        message=f"User {action} successfully",
        user_id=user_id
    )

@router.delete("/users/{user_id}", response_model=AdminActionResponse)
async def delete_user_endpoint(
    user_id: int,
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete user (admin only)."""
    # Prevent self-deletion
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )
    
    # Get user to check if exists and if admin
    user_to_delete = get_user(db, user_id)
    if not user_to_delete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent deleting admin users (safety measure)
    if user_to_delete.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete admin users"
        )
    
    # Delete user
    try:
        db.delete(user_to_delete)
        db.commit()
        
        return AdminActionResponse(
            success=True,
            message=f"User {user_to_delete.full_name or user_to_delete.username} deleted successfully",
            user_id=user_id
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )