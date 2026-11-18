from pydantic import BaseModel, field_validator
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
import json
from app.models.answer import AnswerStatus
from app.core.pagination import PaginatedResponse

# Validator handles flexible sources parsing


class AnswerCreate(BaseModel):
    session_id: int
    execution_id: Optional[int] = None
    section_id: Optional[int] = None
    question_id: Optional[int] = None
    dd_type_id: Optional[int] = None
    answer_text: Optional[str] = None
    sources: Optional[Dict[str, Any]] = None
    confidence_score: Optional[float] = None


class AnswerUpdate(BaseModel):
    answer_text: str
    edit_reason: Optional[str] = None
    sources: Optional[Union[Dict[str, Any], List[Any]]] = None

    @field_validator('sources', mode='before')
    @classmethod
    def parse_sources(cls, v):
        """Parse sources from string to dict/list if needed"""
        if v is None:
            return None
        if isinstance(v, (dict, list)):
            return v
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, (dict, list)) else None
            except (json.JSONDecodeError, ValueError):
                return None
        return None


class AnswerResponse(BaseModel):
    id: int
    session_id: int
    execution_id: Optional[int]
    dd_type_id: Optional[int]
    dd_type_code: Optional[str] = None  # For display purposes
    section_code: Optional[str] = None  # Legacy field for display
    question_code: Optional[str] = None  # Legacy field for display
    answer_text: Optional[str]
    sources: Optional[Any] = None  # Accept any type, validator will convert to dict
    confidence_score: Optional[float]
    tokens_used: int = 0
    status: AnswerStatus

    # Version control fields
    version: int = 1
    is_current: bool = True
    edited_by: Optional[int] = None
    edited_at: Optional[datetime] = None

    # Computed field for edit status
    is_edited: bool = False
    retry_count: int = 0
    answered_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    # Relationships
    editor_name: Optional[str] = None
    session_name: Optional[str] = None
    section_name: Optional[str] = None
    question_text: Optional[str] = None
    validation_status: Optional[str] = None
    total_validations: int = 0

    # OpenAI tracking
    openai_message_ids: List[str] = []

    @field_validator('sources', mode='before')
    @classmethod
    def parse_sources(cls, v):
        """Parse sources from string/list to appropriate format"""
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                # Return parsed value as-is (list or dict) to preserve structure
                return parsed if isinstance(parsed, (dict, list)) else {"value": parsed}
            except (json.JSONDecodeError, ValueError):
                return {"value": v}
        if isinstance(v, list):
            # Return list directly instead of wrapping
            return v
        return {"value": str(v)}

    class Config:
        from_attributes = True


class AnswerWithHistory(BaseModel):
    """Answer with its complete history"""
    answer: AnswerResponse
    history: List[Dict[str, Any]] = []
    validations: List[Dict[str, Any]] = []
    
    class Config:
        from_attributes = True


# Paginated response types
class PaginatedAnswerResponse(PaginatedResponse[AnswerResponse]):
    """Paginated response for answer lists"""
    pass


class AnswerListResponse(BaseModel):
    """Answer list response with pagination and filter info"""
    answers: List[AnswerResponse]
    pagination: Dict[str, Any]
    filters: Optional[Dict[str, Any]] = None
    stats: Optional[Dict[str, Any]] = None  # Optional statistics
    
    @classmethod
    def from_paginated(
        cls,
        paginated: PaginatedAnswerResponse,
        filters: Optional[Dict[str, Any]] = None,
        stats: Optional[Dict[str, Any]] = None
    ) -> 'AnswerListResponse':
        """Convert from paginated response to detailed format"""
        return cls(
            answers=paginated.items,
            pagination={
                "page": paginated.meta.page,
                "limit": paginated.meta.limit,
                "total_items": paginated.meta.total_items,
                "total_pages": paginated.meta.total_pages,
                "has_next": paginated.meta.has_next,
                "has_previous": paginated.meta.has_previous
            },
            filters=filters,
            stats=stats
        )