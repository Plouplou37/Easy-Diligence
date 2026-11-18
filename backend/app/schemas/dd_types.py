from datetime import datetime

from pydantic import BaseModel


class DDTypeResponse(BaseModel):
    id: int  # Primary key
    code: str  # Unique business identifier
    name: str
    description: str | None
    icon: str | None
    is_active: bool
    is_system: bool
    is_validated: bool
    order_index: int
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DDTypeCreate(BaseModel):
    code: str
    name: str
    description: str | None = None
    icon: str | None = None
    order_index: int = 0


class DDTypeUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    description: str | None = None
    icon: str | None = None
    is_active: bool | None = None
    order_index: int | None = None
