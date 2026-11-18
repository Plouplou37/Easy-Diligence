"""
Pagination utilities for API endpoints
"""
from typing import TypeVar, Generic, List, Optional, Any, Dict
from pydantic import BaseModel
from sqlalchemy.orm import Query
from sqlalchemy import func
from math import ceil


T = TypeVar('T')


class PaginationParams(BaseModel):
    """Standard pagination parameters"""
    page: int = 1
    limit: int = 50
    
    @property
    def offset(self) -> int:
        """Calculate offset from page and limit"""
        return (self.page - 1) * self.limit
    
    def model_post_init(self, __context: Any) -> None:
        """Validate pagination parameters"""
        if self.page < 1:
            self.page = 1
        if self.limit < 1:
            self.limit = 1
        if self.limit > 1000:
            self.limit = 1000


class PaginationMeta(BaseModel):
    """Pagination metadata"""
    page: int
    limit: int
    total_items: int
    total_pages: int
    has_next: bool
    has_previous: bool
    
    @classmethod
    def from_params(
        cls, 
        params: PaginationParams, 
        total_items: int
    ) -> 'PaginationMeta':
        """Create pagination metadata from params and total count"""
        total_pages = ceil(total_items / params.limit) if params.limit > 0 else 0
        
        return cls(
            page=params.page,
            limit=params.limit,
            total_items=total_items,
            total_pages=total_pages,
            has_next=params.page < total_pages,
            has_previous=params.page > 1
        )


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response"""
    items: List[T]
    meta: PaginationMeta
    
    @classmethod
    def from_query(
        cls,
        query: Query,
        params: PaginationParams,
        items: List[T]
    ) -> 'PaginatedResponse[T]':
        """Create paginated response from SQLAlchemy query and items"""
        total_items = query.count()
        meta = PaginationMeta.from_params(params, total_items)
        
        return cls(items=items, meta=meta)


def paginate_query(query: Query, params: PaginationParams) -> Query:
    """Apply pagination to SQLAlchemy query"""
    return query.offset(params.offset).limit(params.limit)


def get_pagination_info(
    total_items: int,
    page: int = 1,
    limit: int = 50
) -> Dict[str, Any]:
    """Get pagination information dict (legacy support)"""
    params = PaginationParams(page=page, limit=limit)
    meta = PaginationMeta.from_params(params, total_items)
    
    return {
        "page": meta.page,
        "limit": meta.limit,
        "total_items": meta.total_items,
        "total_pages": meta.total_pages,
        "has_next": meta.has_next,
        "has_previous": meta.has_previous,
        "offset": params.offset
    }