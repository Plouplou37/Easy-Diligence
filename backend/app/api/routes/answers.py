"""Answers: listing, review (edit, status, revert, history), regeneration, PDF export."""

from typing import Any

from fastapi import APIRouter, Body, Depends, File, Form, Response, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from sqlmodel import col

from app.api.deps import get_accessible_session, get_current_active_user
from app.api.uploads import read_upload
from app.core.database import get_db
from app.core.exceptions import InvalidRequestError
from app.core.pagination import PaginationMeta, PaginationParams
from app.exports import pdf
from app.models.answer import (
    AnswerListResponse,
    AnswerResponse,
    AnswerUpdate,
    DDAnswer,
)
from app.models.answer_history import AnswerHistoryResponse, AnswerVersionHistory
from app.models.session import DDSession
from app.models.summary import DDSummary
from app.models.user import User
from app.services import answers as answers_service

router = APIRouter()


def _answer(
    answer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DDAnswer:
    """The answer of the `{answer_id}` path parameter, if the user may access it."""
    return answers_service.get_answer_for_user(db, answer_id, current_user)


def _list_response(
    db: Session,
    answers: list[DDAnswer],
    total: int,
    params: PaginationParams,
    filters: dict[str, Any],
    include_stats: bool,
    extra_stats: dict[str, Any] | None = None,
) -> AnswerListResponse:
    items = answers_service.to_responses(db, answers)
    stats = None
    if include_stats:
        stats = {**(extra_stats or {}), **answers_service.page_stats(items)}
    return AnswerListResponse.of(items, PaginationMeta.from_params(params, total), filters, stats)


@router.get("/all", response_model=AnswerListResponse)
def get_all_answers(
    session_id: int | None = None,
    dd_type: str | None = None,
    status: str | None = None,
    validation_status: str | None = None,
    user_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = 1,
    limit: int = 50,
    search: str | None = None,
    include_stats: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """The current answers of every session the user may see, newest first."""
    params = PaginationParams(page=page, limit=limit)
    answers, total, filters = answers_service.list_answers(
        db,
        current_user,
        params,
        session_id=session_id,
        dd_type=dd_type,
        status=status,
        validation_status=validation_status,
        edited_by=user_id,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )
    return _list_response(db, answers, total, params, filters, include_stats)


@router.get("/stats")
def get_answer_statistics(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """Counts over the current answers of the user's sessions."""
    return answers_service.statistics(db, current_user)


@router.get("/session/{session_identifier}", response_model=AnswerListResponse)
def get_session_answers(
    dd_type: str | None = None,
    section_code: str | None = None,
    execution_id: int | None = None,
    include_history: bool = False,
    page: int = 1,
    limit: int = 100,
    search: str | None = None,
    include_stats: bool = False,
    session: DDSession = Depends(get_accessible_session),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """The answers of a session, in the order they were produced."""
    params = PaginationParams(page=page, limit=limit)
    answers, total, filters = answers_service.list_answers(
        db,
        current_user,
        params,
        session=session,
        dd_type=dd_type,
        section_code=section_code,
        execution_id=execution_id,
        search=search,
        include_history=include_history,
    )
    return _list_response(
        db, answers, total, params, filters, include_stats, {"session_name": session.name}
    )


@router.put("/{answer_id}", response_model=AnswerResponse)
def update_answer(
    data: AnswerUpdate,
    answer: DDAnswer = Depends(_answer),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """A reviewer's edit: a new version, to be reviewed."""
    answers_service.edit_answer(db, answer, data, current_user)
    return answers_service.to_response(db, answer)


@router.post("/{answer_id}/regenerate", response_model=AnswerResponse)
async def regenerate_answer(
    instruction: str | None = Form(None),
    reference_url: str | None = Form(None),
    file: UploadFile | None = File(None),
    answer: DDAnswer = Depends(_answer),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Answer the question again, optionally guided by an instruction, a URL to
    consult, or a document added to the session's vector store. Creates a new
    version, to be reviewed."""
    upload = None
    if file is not None and file.filename:
        upload = (await read_upload(file), file.filename)

    updated = await run_in_threadpool(
        answers_service.regenerate_answer,
        db,
        answer,
        current_user,
        (instruction or "").strip() or None,
        (reference_url or "").strip() or None,
        upload,
    )
    return answers_service.to_response(db, updated)


@router.patch("/{answer_id}/status", response_model=AnswerResponse)
def update_answer_status(
    body: dict[str, Any] = Body(...),
    answer: DDAnswer = Depends(_answer),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Set a reviewer's verdict: `needs_review` or `approved`."""
    answers_service.set_status(db, answer, body.get("status"), current_user)
    return answers_service.to_response(db, answer)


@router.post("/{answer_id}/revert", response_model=AnswerResponse)
def revert_answer(
    body: dict[str, Any] = Body(...),
    answer: DDAnswer = Depends(_answer),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Bring back an earlier version (`version`), as a new version."""
    answers_service.revert_answer(db, answer, body.get("version"), current_user)
    return answers_service.to_response(db, answer)


@router.get("/{answer_id}/history", response_model=AnswerVersionHistory)
def get_answer_history(answer: DDAnswer = Depends(_answer), db: Session = Depends(get_db)):
    """Every version of an answer, newest first."""
    versions = []
    for entry in answers_service.history(db, answer):
        version = AnswerHistoryResponse.model_validate(entry)
        version.editor_name = entry.editor.username if entry.editor else None
        versions.append(version)
    return AnswerVersionHistory(
        answer_id=answer.id or 0,
        current_version=answer.version or 1,
        versions=versions,
        total_versions=len(versions),
    )


@router.get("/session/{session_identifier}/export")
def export_session_answers(
    format: str = "pdf",
    session: DDSession = Depends(get_accessible_session),
    db: Session = Depends(get_db),
):
    """The session's report, as a PDF: the syntheses, then every answer."""
    if format.lower() != "pdf":
        raise InvalidRequestError("Only the PDF export is available")
    answers = answers_service.answers_for_export(db, session)
    summaries = db.query(DDSummary).filter(col(DDSummary.session_id) == session.id).all()
    return Response(
        content=pdf.build_report(session, answers, summaries),
        media_type=pdf.MEDIA_TYPE,
        headers={"Content-Disposition": f"attachment; filename={pdf.report_filename(session)}"},
    )
