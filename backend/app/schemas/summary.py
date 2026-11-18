from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DDSummaryResponse(BaseModel):
    id: int
    session_id: int
    dd_type_id: int
    section_id: Optional[int] = None  # NULL = DD-type synthesis, set = section summary
    summary_text: str
    edited_by: Optional[int] = None
    generated_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # Convenience labels for the frontend (populated by the API layer)
    dd_type_code: Optional[str] = None
    dd_type_name: Optional[str] = None
    section_title: Optional[str] = None

    class Config:
        from_attributes = True


class DDSummaryUpdate(BaseModel):
    summary_text: str


class DDSummaryBatchResponse(BaseModel):
    """State of the OpenAI Batch job producing a DD type's section summaries.

    'status' carries OpenAI's own values (validating, in_progress, completed,
    failed, expired, cancelled), plus 'collected' once the results have been
    stored and the synthesis generated, and 'none' when no batch exists.
    """
    status: str
    message: Optional[str] = None
    openai_batch_id: Optional[str] = None
    # Progress counts, when OpenAI reports them
    completed: Optional[int] = None
    total: Optional[int] = None
    # Number of section summaries stored, once collected
    sections: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
