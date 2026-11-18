"""Answers: listing, review (edit, status, revert, history), export, regeneration."""

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload
from sqlmodel import col

from app.core.cache import CacheInvalidator
from app.core.exceptions import InvalidRequestError, NotFoundError
from app.core.pagination import PaginationParams, paginate_query
from app.models.answer import AnswerResponse, AnswerStatus, AnswerUpdate, DDAnswer
from app.models.answer_history import DDAnswerHistory
from app.models.base import relation, stored_id
from app.models.dd_types import DDType
from app.models.message import DDMessage
from app.models.questions import DDQuestion, DDSection
from app.models.response import DDResponse
from app.models.session import DDSession
from app.models.user import User
from app.models.vector_store import SessionVectorStore, VectorStore
from app.services import vector_stores
from app.services.authz import assert_session_access, filter_sessions_for_user
from app.services.dd_types import get_dd_type_by_code
from app.services.processing import build_company_info, vector_store_ids_for

logger = logging.getLogger(__name__)

# The statuses a reviewer may set by hand.
REVIEW_STATUSES = (AnswerStatus.NEEDS_REVIEW, AnswerStatus.APPROVED)

# Answer status -> the validation status the review page still reads.
_VALIDATION_STATUS = {
    AnswerStatus.APPROVED: "approved",
    AnswerStatus.REJECTED: "rejected",
    AnswerStatus.NEEDS_REVIEW: "pending",
    AnswerStatus.DRAFT: "pending",
}
_PENDING = [AnswerStatus.NEEDS_REVIEW, AnswerStatus.DRAFT]


# --- Lookup and serialisation ---------------------------------------------------


def get_answer_for_user(db: Session, answer_id: int, user: User) -> DDAnswer:
    """The answer, if the user may access its session (404 if unknown, 403 if not theirs)."""
    answer = db.get(DDAnswer, answer_id)
    if answer is None:
        raise NotFoundError("Answer not found")
    if answer.session is not None:
        assert_session_access(answer.session, user)
    return answer


_SOURCE_KEYS = ("type", "filenames", "queries", "content", "url")


def normalise_sources(raw: Any) -> Any:
    """Sources as the review page expects them: the engine's dict as is, a list
    of references kept only if one of them carries something, {} otherwise."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw) if raw else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    if raw is None:
        return {}
    if isinstance(raw, list):
        useful = any(
            isinstance(item, dict) and any(item.get(key) for key in _SOURCE_KEYS) for item in raw
        )
        return raw if useful else {}
    return raw


def _message_ids_by_execution(db: Session, execution_ids: set[int]) -> dict[int, list[str]]:
    """The OpenAI message ids of each execution, in one query."""
    if not execution_ids:
        return {}
    rows = (
        db.query(col(DDResponse.execution_id), col(DDMessage.openai_message_id))
        .select_from(DDMessage)
        .join(DDResponse, col(DDMessage.response_id) == col(DDResponse.response_id))
        .filter(
            col(DDResponse.execution_id).in_(execution_ids),
            col(DDMessage.openai_message_id).isnot(None),
        )
        .all()
    )
    ids: dict[int, list[str]] = {}
    for execution_id, message_id in rows:
        ids.setdefault(execution_id, []).append(message_id)
    return ids


def to_responses(db: Session, answers: list[DDAnswer]) -> list[AnswerResponse]:
    """Answers as the API returns them, with the labels the review page shows."""
    message_ids = _message_ids_by_execution(
        db, {a.execution_id for a in answers if a.execution_id is not None}
    )
    responses = []
    for answer in answers:
        data = answer.model_dump()
        status = answer.status
        data.update(
            sources=normalise_sources(answer.sources),
            session_name=answer.session.name if answer.session else None,
            section_name=answer.section.title if answer.section else None,
            question_text=answer.question.question_text if answer.question else None,
            editor_name=answer.editor.username if answer.editor else None,
            dd_type_code=answer.dd_type_obj.code if answer.dd_type_obj else None,
            validation_status=_VALIDATION_STATUS.get(status) if status else None,
            total_validations=1 if status in (AnswerStatus.APPROVED, AnswerStatus.REJECTED) else 0,
            openai_message_ids=message_ids.get(answer.execution_id or 0, []),
        )
        responses.append(AnswerResponse(**data))
    return responses


def to_response(db: Session, answer: DDAnswer) -> AnswerResponse:
    return to_responses(db, [answer])[0]


# --- Listing ----------------------------------------------------------------------


def list_answers(
    db: Session,
    user: User,
    params: PaginationParams,
    *,
    session: DDSession | None = None,
    session_id: int | None = None,
    dd_type: str | None = None,
    section_code: str | None = None,
    execution_id: int | None = None,
    status: str | None = None,
    validation_status: str | None = None,
    edited_by: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    search: str | None = None,
    include_history: bool = False,
) -> tuple[list[DDAnswer], int, dict[str, Any]]:
    """Answers the user may see, filtered: those of one session, or of all their
    sessions. Current versions only unless include_history.

    Returns the page, the total count and the filters that were applied.
    """
    query = db.query(DDAnswer).options(
        joinedload(relation(DDAnswer.session)),
        joinedload(relation(DDAnswer.section)),
        joinedload(relation(DDAnswer.question)),
        joinedload(relation(DDAnswer.editor)),
    )
    filters: dict[str, Any] = {}

    if session is not None:
        query = query.filter(col(DDAnswer.session_id) == session.id)
        filters["session_id"] = session.id
    else:
        query = filter_sessions_for_user(
            query.join(DDSession, col(DDAnswer.session_id) == col(DDSession.id)), user
        )
        if session_id:
            query = query.filter(col(DDAnswer.session_id) == session_id)
            filters["session_id"] = session_id

    if dd_type:
        dd_type_obj = get_dd_type_by_code(db, dd_type)
        query = query.filter(col(DDAnswer.dd_type_id) == dd_type_obj.id)
        filters["dd_type"] = dd_type
    if section_code:
        # Section codes (A, B...) repeat from one questionnaire to the next.
        if not dd_type:
            raise InvalidRequestError("Filtering by section_code needs the dd_type too")
        query = query.join(DDSection, col(DDAnswer.section_id) == col(DDSection.id)).filter(
            col(DDSection.section_code) == section_code
        )
        filters["section_code"] = section_code
    if execution_id:
        query = query.filter(col(DDAnswer.execution_id) == execution_id)
        filters["execution_id"] = execution_id
    if status:
        query = query.filter(col(DDAnswer.status) == status)
        filters["status"] = status
    if validation_status:
        if validation_status == "pending":
            query = query.filter(col(DDAnswer.status).in_(_PENDING))
        elif validation_status in ("approved", "rejected"):
            query = query.filter(col(DDAnswer.status) == validation_status)
        filters["validation_status"] = validation_status
    if edited_by:
        query = query.filter(col(DDAnswer.edited_by) == edited_by)
        filters["user_id"] = edited_by
    if date_from:
        query = query.filter(col(DDAnswer.created_at) >= date_from)
        filters["date_from"] = date_from
    if date_to:
        query = query.filter(col(DDAnswer.created_at) <= date_to)
        filters["date_to"] = date_to
    if search:
        term = f"%{search}%"
        query = query.outerjoin(DDQuestion, col(DDAnswer.question_id) == col(DDQuestion.id)).filter(
            or_(col(DDAnswer.answer_text).ilike(term), col(DDQuestion.question_text).ilike(term))
        )
        filters["search"] = search
    if not include_history:
        query = query.filter(col(DDAnswer.is_current).is_(True))
        if session is not None:
            filters["include_history"] = False

    if session is not None:
        query = query.order_by(col(DDAnswer.created_at))
    else:
        query = query.order_by(col(DDAnswer.created_at).desc())

    total = query.count()
    return paginate_query(query, params).all(), total, filters


def page_stats(answers: list[AnswerResponse]) -> dict[str, Any]:
    """Figures on a page of answers, for the review page."""
    count = len(answers)
    validated = sum(1 for a in answers if a.validation_status == "approved")
    confidence = sum(a.confidence_score or 0 for a in answers) / count if count else 0
    return {
        "total_answers": count,
        "answers_with_content": sum(1 for a in answers if a.answer_text),
        "validated_answers": validated,
        "average_confidence": round(confidence, 2),
        "validation_rate": round(validated / count * 100, 2) if count else 0,
    }


def statistics(db: Session, user: User) -> dict[str, Any]:
    """Counts over the current answers of the user's sessions."""

    def current() -> Any:
        query = db.query(DDAnswer).join(DDSession, col(DDAnswer.session_id) == col(DDSession.id))
        return filter_sessions_for_user(query, user).filter(col(DDAnswer.is_current).is_(True))

    week_ago = datetime.now(UTC) - timedelta(days=7)
    return {
        "total_answers": current().count(),
        "status_counts": {
            status.value: current().filter(col(DDAnswer.status) == status).count()
            for status in AnswerStatus
        },
        "pending_validations": current().filter(col(DDAnswer.status).in_(_PENDING)).count(),
        "validated_answers": current()
        .filter(col(DDAnswer.status) == AnswerStatus.APPROVED)
        .count(),
        "recent_activity": {
            "new_answers": current().filter(col(DDAnswer.created_at) >= week_ago).count(),
            "recent_edits": current()
            .filter(col(DDAnswer.edited_at) >= week_ago, col(DDAnswer.edited_by).isnot(None))
            .count(),
        },
    }


def answers_for_export(db: Session, session: DDSession) -> list[DDAnswer]:
    """The current answers of a session, in questionnaire order.

    Current versions only: superseded versions and failed attempts stay in the
    table, and a regenerated question used to appear twice in the report.
    """
    answers = (
        db.query(DDAnswer)
        .outerjoin(DDSection, col(DDAnswer.section_id) == col(DDSection.id))
        .outerjoin(DDQuestion, col(DDAnswer.question_id) == col(DDQuestion.id))
        .outerjoin(DDType, col(DDAnswer.dd_type_id) == col(DDType.id))
        .filter(col(DDAnswer.session_id) == session.id, col(DDAnswer.is_current).is_(True))
        # The questionnaire's own order, not the codes': an imported reference
        # need not sort like the questions it numbers.
        .order_by(
            col(DDType.code),
            col(DDSection.order_index),
            col(DDQuestion.order_index),
            col(DDAnswer.id),
        )
        .all()
    )
    if not answers:
        raise NotFoundError("No answers found for session")
    return answers


# --- Review -----------------------------------------------------------------------


def _new_version(
    db: Session,
    answer: DDAnswer,
    user: User,
    text: str,
    sources: Any,
    reason: str,
) -> DDAnswer:
    """Record a new version of the answer (in its history too), to be reviewed."""
    version = (answer.version or 1) + 1
    db.add(
        DDAnswerHistory(
            answer_id=stored_id(answer),
            version=version,
            content=text,
            sources=sources,
            edited_by=user.id,
            edit_reason=reason,
        )
    )
    answer.version = version
    answer.status = AnswerStatus.NEEDS_REVIEW
    answer.edited_by = user.id
    answer.edited_at = datetime.now(UTC)
    answer.answer_text = text
    answer.sources = sources
    db.commit()
    db.refresh(answer)
    return answer


def edit_answer(db: Session, answer: DDAnswer, data: AnswerUpdate, user: User) -> DDAnswer:
    """A reviewer's edit: a new version, back to review."""
    return _new_version(
        db, answer, user, data.answer_text, data.sources, data.edit_reason or "Manual edit"
    )


def revert_answer(db: Session, answer: DDAnswer, version: Any, user: User) -> DDAnswer:
    """Bring back an earlier version, as a new version."""
    if not version:
        raise InvalidRequestError("Target version is required")
    target = (
        db.query(DDAnswerHistory)
        .filter(
            col(DDAnswerHistory.answer_id) == answer.id,
            col(DDAnswerHistory.version) == version,
        )
        .first()
    )
    if target is None:
        raise NotFoundError(f"Version {version} not found")
    return _new_version(
        db, answer, user, target.content, target.sources, f"Reverted to version {version}"
    )


def set_status(db: Session, answer: DDAnswer, status: Any, user: User) -> DDAnswer:
    """A reviewer's verdict: needs review, or approved."""
    if not status:
        raise InvalidRequestError("Status is required")
    allowed = [s.value for s in REVIEW_STATUSES]
    if status not in allowed:
        raise InvalidRequestError(f"Status must be one of: {', '.join(allowed)}")
    answer.status = AnswerStatus(status)
    answer.edited_by = user.id
    answer.edited_at = datetime.now(UTC)
    db.commit()
    db.refresh(answer)
    return answer


def history(db: Session, answer: DDAnswer) -> list[DDAnswerHistory]:
    """Every version of the answer, newest first."""
    return (
        db.query(DDAnswerHistory)
        .filter(col(DDAnswerHistory.answer_id) == answer.id)
        .order_by(col(DDAnswerHistory.version).desc())
        .all()
    )


# --- Regeneration -------------------------------------------------------------------


def regenerate_answer(
    db: Session,
    answer: DDAnswer,
    user: User,
    instruction: str | None = None,
    reference_url: str | None = None,
    upload: tuple[bytes, str] | None = None,
) -> DDAnswer:
    """Answer the question again, in the context of the run's earlier answers.

    Optional guidance: an instruction, a URL the model is told to consult, and
    a document (content, filename) added to the session's vector store, kept for
    later questions and cited in the new answer's sources. Creates a new
    version, to be reviewed.

    Blocking (OpenAI): call it from a worker thread.
    """
    # Imported here: the engine pulls in the OpenAI client and its settings.
    from app.engine.processor import DDProcessor

    execution, session = answer.execution, answer.session
    if execution is None or answer.question is None or session is None:
        raise InvalidRequestError(
            "This answer cannot be regenerated (missing execution or question)."
        )
    dd_type = execution.dd_type
    if dd_type is None or dd_type.id is None:
        raise InvalidRequestError("DD type not resolvable for this answer.")

    store_ids = vector_store_ids_for(db, answer.session_id, dd_type.id)
    extra_source = None
    if upload is not None:
        content, filename = upload
        client = vector_stores.openai_client()
        if store_ids:
            store_id = store_ids[0]
        else:
            # No store for this run yet: one for the session and this DD type.
            name = f"{session.session_code or f'session-{answer.session_id}'}-regen"
            store_id = client.create_vector_store(name=name)
            db.add(VectorStore(id=store_id, name=name, created_by=stored_id(user)))
            db.add(
                SessionVectorStore(
                    session_id=answer.session_id,
                    dd_type_id=dd_type.id,
                    vector_store_id=store_id,
                    assigned_by=stored_id(user),
                )
            )
            db.commit()
            store_ids = [store_id]
        file_id = client.upload_file(content, filename)
        client.add_file_to_vector_store(store_id, file_id)
        CacheInvalidator.invalidate_vector_store_cache()
        # Best effort, so that file_search sees the document on the first try.
        client.wait_for_file_indexed(store_id, file_id, timeout=30)
        extra_source = {"type": "file_search", "file_id": file_id, "filename": filename}

    processor = DDProcessor(answer.session_id, dd_type.code)
    return processor.regenerate_single_answer(
        db,
        answer,
        store_ids,
        build_company_info(session.company),
        instruction,
        reference_url,
        extra_source,
    )
