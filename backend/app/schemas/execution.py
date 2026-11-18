from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.execution import ExecutionStatus


class ExecutionCreate(BaseModel):
    session_id: int
    dd_type_id: int


class ExecutionUpdate(BaseModel):
    status: ExecutionStatus | None = None
    conversation_id: str | None = None


class ExecutionValidate(BaseModel):
    validation_comments: str | None = None


class ExecutionResponse(BaseModel):
    id: int
    session_id: int
    dd_type_id: int
    dd_type_code: str | None = None  # For display purposes
    status: ExecutionStatus
    conversation_id: str | None
    validated_at: datetime | None
    validated_by: int | None
    created_at: datetime
    updated_at: datetime

    # Relationships
    validator_name: str | None = None
    dd_type_name: str | None = None
    total_responses: int | None = None
    total_answers: int | None = None

    # Error feedback when execution fails
    failure_info: dict[str, Any] | None = None

    class Config:
        from_attributes = True


class ExecutionSummary(BaseModel):
    id: int
    dd_type_id: int
    dd_type_code: str | None = None  # For display purposes
    dd_type_name: str
    status: ExecutionStatus
    created_at: datetime
    updated_at: datetime
    total_answers: int = 0
    validated_answers: int = 0
    pending_answers: int = 0

    class Config:
        from_attributes = True
