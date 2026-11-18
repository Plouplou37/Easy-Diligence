from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.execution import ExecutionStatus

class ExecutionCreate(BaseModel):
    session_id: int
    dd_type_id: int

class ExecutionUpdate(BaseModel):
    status: Optional[ExecutionStatus] = None
    conversation_id: Optional[str] = None

class ExecutionValidate(BaseModel):
    validation_comments: Optional[str] = None

class ExecutionResponse(BaseModel):
    id: int
    session_id: int
    dd_type_id: int
    dd_type_code: Optional[str] = None  # For display purposes
    status: ExecutionStatus
    conversation_id: Optional[str]
    validated_at: Optional[datetime]
    validated_by: Optional[int]
    created_at: datetime
    updated_at: datetime

    # Relationships
    validator_name: Optional[str] = None
    dd_type_name: Optional[str] = None
    total_responses: Optional[int] = None
    total_answers: Optional[int] = None

    # Error feedback when execution fails
    failure_info: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

class ExecutionSummary(BaseModel):
    id: int
    dd_type_id: int
    dd_type_code: Optional[str] = None  # For display purposes
    dd_type_name: str
    status: ExecutionStatus
    created_at: datetime
    updated_at: datetime
    total_answers: int = 0
    validated_answers: int = 0
    pending_answers: int = 0
    
    class Config:
        from_attributes = True