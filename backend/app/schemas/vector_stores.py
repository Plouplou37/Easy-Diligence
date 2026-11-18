from datetime import datetime

from pydantic import BaseModel, ConfigDict


class VectorStoreCreate(BaseModel):
    name: str
    description: str | None = None
    expires_after_days: int | None = None


class VectorStoreUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class VectorStoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None = None
    file_count: int
    total_bytes: int
    status: str
    expires_after_days: int | None = None
    expires_at: datetime | None = None
    last_active_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None


class SessionVectorStoreAssignment(BaseModel):
    vector_store_id: str | None = None  # Optional since it's in URL path
    dd_type_id: int | None = None  # None = whole session
