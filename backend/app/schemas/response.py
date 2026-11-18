from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ResponseCreate(BaseModel):
    execution_id: int
    response_id: str
    previous_response_id: str | None = None
    openai_response: dict[str, Any]


class ResponseResponse(BaseModel):
    id: int
    execution_id: int
    response_id: str
    previous_response_id: str | None
    openai_response: dict[str, Any]
    created_at: datetime

    # Relationships
    message_count: int | None = None

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    """Full conversation chain for an execution"""

    execution_id: int
    conversation_id: str
    responses: list[ResponseResponse]
    total_responses: int

    class Config:
        from_attributes = True
