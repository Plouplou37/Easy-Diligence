from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class UserListItem(BaseModel):
    """User information for admin list view"""
    id: int
    username: str
    email: EmailStr
    full_name: Optional[str]
    company: Optional[str]
    role: str
    is_active: bool
    is_verified: bool
    last_login: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserListResponse(BaseModel):
    """Paginated user list response"""
    users: List[UserListItem]
    total: int
    page: int
    per_page: int
    total_pages: int

class UserRoleUpdate(BaseModel):
    """Schema for updating user role"""
    role: str
    
    class Config:
        schema_extra = {
            "example": {
                "role": "admin"
            }
        }

class UserStatusUpdate(BaseModel):
    """Schema for updating user status"""
    is_active: bool
    
    class Config:
        schema_extra = {
            "example": {
                "is_active": True
            }
        }

class AdminActionResponse(BaseModel):
    """Standard response for admin actions"""
    success: bool
    message: str
    user_id: Optional[int] = None