from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.schemas.user import Role


class UserListItem(BaseModel):
    """User information for admin list view"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    full_name: str | None
    company: str | None
    role: str
    is_active: bool
    is_verified: bool
    last_login: datetime | None
    created_at: datetime


class UserListResponse(BaseModel):
    """Paginated user list response"""

    users: list[UserListItem]
    total: int
    page: int
    per_page: int
    total_pages: int


class UserRoleUpdate(BaseModel):
    """Schema for updating user role (anything but admin/analyst is a 422)"""

    model_config = ConfigDict(json_schema_extra={"example": {"role": "admin"}})

    role: Role


class UserStatusUpdate(BaseModel):
    """Schema for updating user status"""

    model_config = ConfigDict(json_schema_extra={"example": {"is_active": True}})

    is_active: bool


class AdminActionResponse(BaseModel):
    """Standard response for admin actions"""

    success: bool
    message: str
    user_id: int | None = None
