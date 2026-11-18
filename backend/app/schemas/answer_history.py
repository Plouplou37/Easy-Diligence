from pydantic import BaseModel, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
import json

class AnswerHistoryCreate(BaseModel):
    answer_id: int
    version: int
    content: str
    sources: Optional[Dict[str, Any]] = None
    edit_reason: Optional[str] = None

class AnswerHistoryResponse(BaseModel):
    id: int
    answer_id: int
    version: int
    content: str
    sources: Optional[Any] = None
    edited_by: Optional[int]
    edit_reason: Optional[str]
    created_at: datetime

    # Relationships
    editor_name: Optional[str] = None

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
    versions: List[AnswerHistoryResponse]
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
    sources_a: Optional[Dict[str, Any]]
    sources_b: Optional[Dict[str, Any]]
    editor_a: Optional[str]
    editor_b: Optional[str]
    created_a: datetime
    created_b: datetime