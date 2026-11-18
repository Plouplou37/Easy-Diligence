import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class AnswerHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
                return parsed if isinstance(parsed, (dict, list)) else {"value": parsed}
            except (json.JSONDecodeError, ValueError):
                return {"value": v}
        if isinstance(v, list):
            return v
        return {"value": str(v)}


class AnswerVersionHistory(BaseModel):
    """Complete version history for an answer"""

    model_config = ConfigDict(from_attributes=True)

    answer_id: int
    current_version: int
    versions: list[AnswerHistoryResponse]
    total_versions: int
