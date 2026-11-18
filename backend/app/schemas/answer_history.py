import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator


class AnswerHistoryCreate(BaseModel):
    answer_id: int
    version: int
    content: str
    sources: dict[str, Any] | None = None
    edit_reason: str | None = None

class AnswerHistoryResponse(BaseModel):
    id: int
    answer_id: int
    version: int
    content: str
    sources: Any | None = None
    edited_by: int | None
    edit_reason: str | None
    created_at: datetime

    # Relationships
    editor_name: str | None = None

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
                return parsed if isinstance(parsed, (dict, list)) else {"value": parsed}
            except (json.JSONDecodeError, ValueError):
                return {"value": v}
        if isinstance(v, list):
            return v
        return {"value": str(v)}

    class Config:
        from_attributes = True

class AnswerVersionHistory(BaseModel):
    """Complete version history for an answer"""
    answer_id: int
    current_version: int
    versions: list[AnswerHistoryResponse]
    total_versions: int

    class Config:
        from_attributes = True

class VersionComparison(BaseModel):
    """Compare two versions of an answer"""
    answer_id: int
    version_a: int
    version_b: int
    content_a: str
    content_b: str
    sources_a: dict[str, Any] | None
    sources_b: dict[str, Any] | None
    editor_a: str | None
    editor_b: str | None
    created_a: datetime
    created_b: datetime
