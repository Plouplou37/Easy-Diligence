from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DDTypeResponse(BaseModel):
    id: int  # Primary key
    code: str  # Unique business identifier
    name: str
    description: Optional[str]
    icon: Optional[str]
    is_active: bool
    is_system: bool
    is_validated: bool
    order_index: int
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DDTypeCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    order_index: int = 0


class DDTypeUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    is_active: Optional[bool] = None
    order_index: Optional[int] = None