from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.session import SessionStatus
from app.core.pagination import PaginatedResponse, PaginationMeta


class SessionCreate(BaseModel):
    company_id: int
    name: str
    description: Optional[str] = None
    dd_type_ids: Optional[List[int]] = None  # Allow users to select specific DD type IDs


class SessionResponse(BaseModel):
    id: int
    session_code: Optional[str] = None
    company_id: int
    name: str
    description: Optional[str]
    status: SessionStatus
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None
    assigned_to: Optional[int] = None
    created_by_username: Optional[str] = None
    dd_types_json: Optional[str] = None  # JSON string of selected DD types for this session
    # The company under review, as two entities (see models/company.py): the
    # fund itself and the company running it (NULL on companies created before
    # the split).
    company_name: Optional[str] = None
    management_company_name: Optional[str] = None
    
    # New execution-related fields
    total_executions: int = 0
    completed_executions: int = 0
    in_progress_executions: int = 0
    validated_executions: int = 0

    class Config:
        from_attributes = True
        
    @classmethod
    def from_db_model(cls, session_db):
        """Custom method to ensure all fields are properly serialized"""
        return cls(
            id=session_db.id,
            session_code=session_db.session_code,
            company_id=session_db.company_id,
            name=session_db.name,
            description=session_db.description,
            status=session_db.status,
            created_at=session_db.created_at,
            updated_at=session_db.updated_at,
            created_by=session_db.created_by,
            assigned_to=session_db.assigned_to,
            created_by_username=getattr(session_db, 'created_by_username', None),
            dd_types_json=session_db.dd_types_json,  # Explicitly include this field
            total_executions=getattr(session_db, 'total_executions', 0),
            completed_executions=getattr(session_db, 'completed_executions', 0),
            in_progress_executions=getattr(session_db, 'in_progress_executions', 0),
            validated_executions=getattr(session_db, 'validated_executions', 0),
            company_name=session_db.company.name if getattr(session_db, 'company', None) else None,
            management_company_name=(
                session_db.company.management_company_name
                if getattr(session_db, 'company', None) else None
            ),
        )


class SessionStatusResponse(BaseModel):
    id: int
    status: SessionStatus
    progress: List[dict]  # Will contain progress for each DD type
    executions: List[Dict[str, Any]] = []  # Execution status for each DD type


class SessionWithExecutions(BaseModel):
    """Session with detailed execution information"""
    session: SessionResponse
    executions: List[Dict[str, Any]] = []
    session_dd_types: List[Dict[str, Any]] = []
    validation_stats: Dict[str, Any] = {}
    
    class Config:
        from_attributes = True


# Paginated response types
class PaginatedSessionResponse(PaginatedResponse[SessionResponse]):
    """Paginated response for session lists"""
    pass


class SessionListResponse(BaseModel):
    """Legacy session list response with pagination info"""
    sessions: List[SessionResponse]
    pagination: Dict[str, Any]
    filters: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_paginated(
        cls,
        paginated: PaginatedSessionResponse,
        filters: Optional[Dict[str, Any]] = None
    ) -> 'SessionListResponse':
        """Convert from paginated response to legacy format"""
        return cls(
            sessions=paginated.items,
            pagination={
                "page": paginated.meta.page,
                "limit": paginated.meta.limit,
                "total_items": paginated.meta.total_items,
                "total_pages": paginated.meta.total_pages,
                "has_next": paginated.meta.has_next,
                "has_previous": paginated.meta.has_previous
            },
            filters=filters
        )