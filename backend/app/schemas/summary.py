from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DDSummaryResponse(BaseModel):
    id: int
    session_id: int
    dd_type_id: int
    section_id: int | None = None  # NULL = DD-type synthesis, set = section summary
    summary_text: str
    edited_by: int | None = None
    generated_at: datetime | None = None
    updated_at: datetime | None = None
    # Convenience labels for the frontend (populated by the API layer)
    dd_type_code: str | None = None
    dd_type_name: str | None = None
    section_title: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DDSummaryUpdate(BaseModel):
    summary_text: str


class DDSummaryBatchResponse(BaseModel):
    """State of the OpenAI Batch job producing a DD type's section summaries.

    'status' carries OpenAI's own values (validating, in_progress, completed,
    failed, expired, cancelled), plus 'collected' once the results have been
    stored and the synthesis generated, and 'none' when no batch exists.
    """

    status: str
    message: str | None = None
    openai_batch_id: str | None = None
    # Progress counts, when OpenAI reports them
    completed: int | None = None
    total: int | None = None
    # Number of section summaries stored, once collected
    sections: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
