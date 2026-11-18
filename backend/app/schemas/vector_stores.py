from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class VectorStoreCreate(BaseModel):
    name: str
    description: Optional[str] = None
    expires_after_days: Optional[int] = None


class VectorStoreUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class VectorStoreResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    file_count: int
    total_bytes: int
    status: str
    expires_after_days: Optional[int] = None
    expires_at: Optional[datetime] = None
    last_active_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SessionVectorStoreAssignment(BaseModel):
    vector_store_id: Optional[str] = None  # Optional since it's in URL path
    dd_type_id: Optional[int] = None  # None = whole session


class VectorStoreSearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 10
    filter: Optional[Dict[str, Any]] = None


class SearchResult(BaseModel):
    file_id: Optional[str]
    filename: Optional[str]
    score: float
    attributes: Dict[str, Any]
    content: List[Dict[str, str]]


class VectorStoreSearchResponse(BaseModel):
    search_query: str
    data: List[SearchResult]
    has_more: bool
    next_page: Optional[str]


# Removed unused batch and file attributes functionality
# These features were not used by the frontend and added unnecessary complexity