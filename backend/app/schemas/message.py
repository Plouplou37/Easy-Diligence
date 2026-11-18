from datetime import datetime
from typing import Any

from pydantic import BaseModel


class MessageCreate(BaseModel):
    response_id: str
    message_index: int
    role: str
    content: str | None = None
    tool_calls: dict[str, Any] | None = None

class MessageResponse(BaseModel):
    id: int
    response_id: str
    message_index: int
    role: str
    content: str | None
    tool_calls: dict[str, Any] | None
    created_at: datetime

    class Config:
        from_attributes = True

class MessagesResponse(BaseModel):
    """All messages for a response"""
    response_id: str
    messages: list[MessageResponse]
    total_messages: int

    class Config:
        from_attributes = True
