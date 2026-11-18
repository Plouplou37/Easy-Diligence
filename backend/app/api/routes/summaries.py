from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.core.utils import get_session_by_identifier
from app.engine.summarizer import (
    cancel_section_summaries_batch,
    collect_section_summaries_batch,
    generate_summaries_for_dd_type,
    submit_section_summaries_batch,
)
from app.models.dd_types import DDType
from app.models.session import DDSession
from app.models.summary import DDSummary
from app.models.user import User
from app.schemas.summary import (
    DDSummaryBatchResponse,
    DDSummaryResponse,
    DDSummaryUpdate,
)
from app.services.authz import assert_session_access

router = APIRouter()


def _to_response(summary: DDSummary) -> DDSummaryResponse:
    """Serialize a DDSummary with convenience labels for the frontend."""
    return DDSummaryResponse(
        id=summary.id,
        session_id=summary.session_id,
        dd_type_id=summary.dd_type_id,
        section_id=summary.section_id,
        summary_text=summary.summary_text,
        edited_by=summary.edited_by,
        generated_at=summary.generated_at,
        updated_at=summary.updated_at,
        dd_type_code=summary.dd_type.code if summary.dd_type else None,
        dd_type_name=summary.dd_type.name if summary.dd_type else None,
        section_title=summary.section.title if summary.section else None,
    )


def _load_session_or_404(db: Session, session_id: int) -> DDSession:
    session = db.query(DDSession).filter(DDSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post(
    "/session/{session_identifier}/dd/{dd_type}/generate", response_model=list[DDSummaryResponse]
)
async def generate_summaries(
    session_identifier: str,
    dd_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Generate section summaries + the DD-type synthesis for a session/DD type."""
    session, session_id = get_session_by_identifier(db, session_identifier)
    assert_session_access(session, current_user)

    summaries = await generate_summaries_for_dd_type(db, session, dd_type)

    return [_to_response(s) for s in summaries]


@router.post(
    "/session/{session_identifier}/dd/{dd_type}/generate/batch",
    response_model=DDSummaryBatchResponse,
)
async def generate_summaries_via_batch(
    session_identifier: str,
    dd_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Queue the section summaries as an OpenAI batch (half price, up to 24h).

    Returns immediately with the job state; poll the GET below to collect the
    results. The synthesis is not queued -- it is derived from the section
    summaries and is generated when the batch is collected.

    Kept apart from the synchronous endpoint rather than folded into it behind a
    flag: the two return different things, and a union response would blur the
    immediate path's contract.
    """
    session, session_id = get_session_by_identifier(db, session_identifier)
    assert_session_access(session, current_user)

    row = submit_section_summaries_batch(db, session, dd_type, current_user.id)

    return DDSummaryBatchResponse(
        status=row.status,
        message="Section summaries queued",
        openai_batch_id=row.openai_batch_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get(
    "/session/{session_identifier}/dd/{dd_type}/batch", response_model=DDSummaryBatchResponse
)
async def get_summary_batch_status(
    session_identifier: str,
    dd_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Refresh a summary batch's state and, once complete, store its results.

    Polled by the frontend. Collection happens here rather than in a background
    task on purpose: BackgroundTasks are in-process and do not survive a restart,
    which is exactly what leaves executions orphaned today. A batch runs for up
    to 24h, far longer than any process is guaranteed to live.
    """
    session, session_id = get_session_by_identifier(db, session_identifier)
    assert_session_access(session, current_user)

    row, info = await collect_section_summaries_batch(db, session, dd_type)

    return DDSummaryBatchResponse(
        status=info["status"],
        message=info.get("message"),
        openai_batch_id=row.openai_batch_id if row else None,
        completed=info.get("completed"),
        total=info.get("total"),
        sections=info.get("sections"),
        created_at=row.created_at if row else None,
        updated_at=row.updated_at if row else None,
    )


@router.post(
    "/session/{session_identifier}/dd/{dd_type}/batch/cancel", response_model=DDSummaryBatchResponse
)
async def cancel_summary_batch(
    session_identifier: str,
    dd_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Cancel a summary batch still running at OpenAI.

    Until this existed, a batch sitting in OpenAI's queue could only be stopped
    from the OpenAI dashboard -- and it kept both generate buttons disabled in
    the meantime. Requests already completed stay billed; the rest are dropped.
    """
    session, session_id = get_session_by_identifier(db, session_identifier)
    assert_session_access(session, current_user)

    row, info = cancel_section_summaries_batch(db, session, dd_type)

    return DDSummaryBatchResponse(
        status=info["status"],
        message=info.get("message"),
        openai_batch_id=row.openai_batch_id if row else None,
        completed=info.get("completed"),
        total=info.get("total"),
        created_at=row.created_at if row else None,
        updated_at=row.updated_at if row else None,
    )


@router.get("/session/{session_identifier}", response_model=list[DDSummaryResponse])
async def list_summaries(
    session_identifier: str,
    dd_type: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List stored summaries for a session (optionally filtered by DD type code)."""
    session, session_id = get_session_by_identifier(db, session_identifier)
    assert_session_access(session, current_user)

    query = db.query(DDSummary).filter(DDSummary.session_id == session_id)
    if dd_type:
        dd_type_obj = db.query(DDType).filter(DDType.code == dd_type).first()
        if not dd_type_obj:
            raise HTTPException(status_code=404, detail=f"DD type '{dd_type}' not found")
        query = query.filter(DDSummary.dd_type_id == dd_type_obj.id)

    summaries = query.all()
    return [_to_response(s) for s in summaries]


@router.put("/{summary_id}", response_model=DDSummaryResponse)
async def update_summary(
    summary_id: int,
    update: DDSummaryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Manually edit a summary's text before export."""
    summary = db.query(DDSummary).filter(DDSummary.id == summary_id).first()
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")

    # Per-user isolation via the owning session
    session = _load_session_or_404(db, summary.session_id)
    assert_session_access(session, current_user)

    summary.summary_text = update.summary_text
    summary.edited_by = current_user.id
    db.commit()
    db.refresh(summary)
    return _to_response(summary)
