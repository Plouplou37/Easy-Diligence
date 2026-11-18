from datetime import datetime
from typing import Any

from pydantic import BaseModel


class VectorStoreCreate(BaseModel):
    name: str
    description: str | None = None
    expires_after_days: int | None = None


class VectorStoreUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class VectorStoreResponse(BaseModel):
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

    class Config:
        from_attributes = True


class SessionVectorStoreAssignment(BaseModel):
    vector_store_id: str | None = None  # Optional since it's in URL path
    dd_type_id: int | None = None  # None = whole session


class VectorStoreSearchRequest(BaseModel):
    query: str
    limit: int | None = 10
    filter: dict[str, Any] | None = None


class SearchResult(BaseModel):
    file_id: str | None
    filename: str | None
    score: float
    attributes: dict[str, Any]
    content: list[dict[str, str]]


class VectorStoreSearchResponse(BaseModel):
    search_query: str
    data: list[SearchResult]
    has_more: bool
    next_page: str | None


# Removed unused batch and file attributes functionality
# These features were not used by the frontend and added unnecessary complexity
