import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.pagination import PaginatedResponse
from app.models.answer import AnswerStatus


class AnswerUpdate(BaseModel):
    answer_text: str
    edit_reason: str | None = None
    sources: dict[str, Any] | list[Any] | None = None

    @field_validator("sources", mode="before")
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
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    execution_id: int | None
    dd_type_id: int | None
    dd_type_code: str | None = None  # For display purposes
    section_code: str | None = None  # Legacy field for display
    question_code: str | None = None  # Legacy field for display
    answer_text: str | None
    sources: Any | None = None  # Accept any type, validator will convert to dict
    confidence_score: float | None
    tokens_used: int = 0
    status: AnswerStatus

    # Version control fields
    version: int = 1
    is_current: bool = True
    edited_by: int | None = None
    edited_at: datetime | None = None

    # Computed field for edit status
    is_edited: bool = False
    retry_count: int = 0
    answered_at: datetime | None
    created_at: datetime
    updated_at: datetime | None

    # Relationships
    editor_name: str | None = None
    session_name: str | None = None
    section_name: str | None = None
    question_text: str | None = None
    validation_status: str | None = None
    total_validations: int = 0

    # OpenAI tracking
    openai_message_ids: list[str] = []

    @field_validator("sources", mode="before")
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


# Paginated response types
class PaginatedAnswerResponse(PaginatedResponse[AnswerResponse]):
    """Paginated response for answer lists"""

    pass


class AnswerListResponse(BaseModel):
    """Answer list response with pagination and filter info"""

    answers: list[AnswerResponse]
    pagination: dict[str, Any]
    filters: dict[str, Any] | None = None
    stats: dict[str, Any] | None = None  # Optional statistics

    @classmethod
    def from_paginated(
        cls,
        paginated: PaginatedAnswerResponse,
        filters: dict[str, Any] | None = None,
        stats: dict[str, Any] | None = None,
    ) -> "AnswerListResponse":
        """Convert from paginated response to detailed format"""
        return cls(
            answers=paginated.items,
            pagination={
                "page": paginated.meta.page,
                "limit": paginated.meta.limit,
                "total_items": paginated.meta.total_items,
                "total_pages": paginated.meta.total_pages,
                "has_next": paginated.meta.has_next,
                "has_previous": paginated.meta.has_previous,
            },
            filters=filters,
            stats=stats,
        )
