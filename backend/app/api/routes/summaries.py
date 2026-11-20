"""Summaries of a session: the section summaries and the DD type synthesis.

Generated now (the model writes them during the request) or through an OpenAI
batch (half price, up to 24 h), then reviewed and edited before the export.

The engine's summary functions are coroutines that also call the database and
OpenAI synchronously. The routes are plain `def`: each runs its coroutine in an
event loop of its own, on the worker thread, so those calls block that thread
and not the server (they used to block it, every 15 s while a batch ran).
"""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_accessible_session, get_current_active_user, get_visible_dd_type
from app.core.database import get_db
from app.engine.summarizer import (
    cancel_section_summaries_batch,
    collect_section_summaries_batch,
    generate_summaries_for_dd_type,
    submit_section_summaries_batch,
)
from app.models.base import stored_id
from app.models.dd_types import DDType
from app.models.session import DDSession
from app.models.summary import (
    DDSummaryBatch,
    DDSummaryBatchResponse,
    DDSummaryResponse,
    DDSummaryUpdate,
)
from app.models.user import User
from app.services import summaries as summaries_service

router = APIRouter()

RUN = "/session/{session_identifier}/dd/{dd_type}"


def _batch_response(
    row: DDSummaryBatch | None, info: dict[str, Any], with_sections: bool = True
) -> DDSummaryBatchResponse:
    return DDSummaryBatchResponse(
        status=info["status"],
        message=info.get("message"),
        openai_batch_id=row.openai_batch_id if row else None,
        completed=info.get("completed"),
        total=info.get("total"),
        sections=info.get("sections") if with_sections else None,
        created_at=row.created_at if row else None,
        updated_at=row.updated_at if row else None,
    )


@router.post(RUN + "/generate", response_model=list[DDSummaryResponse])
def generate_summaries(
    session: DDSession = Depends(get_accessible_session),
    dd_type: DDType = Depends(get_visible_dd_type),
    db: Session = Depends(get_db),
):
    """Write the section summaries and the DD type synthesis now."""
    summaries = generate_summaries_for_dd_type(db, session, dd_type.code)
    return [summaries_service.to_response(s) for s in summaries]


@router.post(RUN + "/generate/batch", response_model=DDSummaryBatchResponse)
def generate_summaries_via_batch(
    session: DDSession = Depends(get_accessible_session),
    dd_type: DDType = Depends(get_visible_dd_type),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Queue the section summaries as an OpenAI batch; the GET below collects
    them. The synthesis is written from the section summaries, at collection."""
    row = submit_section_summaries_batch(db, session, dd_type.code, stored_id(current_user))
    return DDSummaryBatchResponse(
        status=row.status,
        message="Section summaries queued",
        openai_batch_id=row.openai_batch_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get(RUN + "/batch", response_model=DDSummaryBatchResponse)
def get_summary_batch_status(
    session: DDSession = Depends(get_accessible_session),
    dd_type: DDType = Depends(get_visible_dd_type),
    db: Session = Depends(get_db),
):
    """Refresh a batch's state and, once it is done, store its results.

    Polled by the page. Collecting here rather than in a background task is on
    purpose: a batch runs for up to 24 h, longer than a process is sure to live.
    """
    row, info = collect_section_summaries_batch(db, session, dd_type.code)
    return _batch_response(row, info)


@router.post(RUN + "/batch/cancel", response_model=DDSummaryBatchResponse)
def cancel_summary_batch(
    session: DDSession = Depends(get_accessible_session),
    dd_type: DDType = Depends(get_visible_dd_type),
    db: Session = Depends(get_db),
):
    """Cancel a batch still running at OpenAI. Requests already done stay billed."""
    row, info = cancel_section_summaries_batch(db, session, dd_type.code)
    return _batch_response(row, info, with_sections=False)


@router.get("/session/{session_identifier}", response_model=list[DDSummaryResponse])
def list_summaries(
    dd_type: str | None = None,
    session: DDSession = Depends(get_accessible_session),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """The stored summaries of a session, of one DD type (its code) if given."""
    summaries = summaries_service.list_summaries(db, session, current_user, dd_type)
    return [summaries_service.to_response(s) for s in summaries]


@router.put("/{summary_id}", response_model=DDSummaryResponse)
def update_summary(
    summary_id: int,
    update: DDSummaryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Edit a summary's text before the export."""
    summary = summaries_service.edit_summary(db, summary_id, update.summary_text, current_user)
    return summaries_service.to_response(summary)
