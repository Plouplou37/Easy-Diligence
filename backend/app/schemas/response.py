from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class ResponseCreate(BaseModel):
    execution_id: int
    response_id: str
    previous_response_id: Optional[str] = None
    openai_response: Dict[str, Any]

class ResponseResponse(BaseModel):
    id: int
    execution_id: int
    response_id: str
    previous_response_id: Optional[str]
    openai_response: Dict[str, Any]
    created_at: datetime
    
    # Relationships
    message_count: Optional[int] = None
    
    class Config:
        from_attributes = True

class ConversationResponse(BaseModel):
    """Full conversation chain for an execution"""
    execution_id: int
    conversation_id: str
    responses: List[ResponseResponse]
    total_responses: int
    
    class Config:
        from_attributes = True