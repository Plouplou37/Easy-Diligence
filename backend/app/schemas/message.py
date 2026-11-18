from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

class MessageCreate(BaseModel):
    response_id: str
    message_index: int
    role: str
    content: Optional[str] = None
    tool_calls: Optional[Dict[str, Any]] = None

class MessageResponse(BaseModel):
    id: int
    response_id: str
    message_index: int
    role: str
    content: Optional[str]
    tool_calls: Optional[Dict[str, Any]]
    created_at: datetime
    
    class Config:
        from_attributes = True

class MessagesResponse(BaseModel):
    """All messages for a response"""
    response_id: str
    messages: List[MessageResponse]
    total_messages: int
    
    class Config:
        from_attributes = True