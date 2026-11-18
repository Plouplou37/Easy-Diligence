import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.api.uploads import read_upload
from app.core.database import get_db
from app.core.pagination import PaginationMeta, PaginationParams, paginate_query
from app.core.utils import build_company_info, get_session_by_identifier
from app.exports.answers import AnswerExporter
from app.models.answer import AnswerStatus, DDAnswer
from app.models.answer_history import DDAnswerHistory
from app.models.questions import DDQuestion, DDSection
from app.models.session import DDSession
from app.models.user import User
from app.schemas.answer import (
    AnswerListResponse,
    AnswerResponse,
    AnswerUpdate,
    AnswerWithHistory,
    PaginatedAnswerResponse,
)
from app.schemas.answer_history import AnswerHistoryResponse, AnswerVersionHistory
from app.services.authz import assert_session_access, filter_sessions_for_user, user_is_admin

router = APIRouter()
logger = logging.getLogger(__name__)


# Helper function to get DD type by code
def get_dd_type_by_code(db: Session, code: str):
    """Helper function to get DD type by code"""
    from app.models.dd_types import DDType

    dd_type = db.query(DDType).filter(DDType.code == code).first()
    if not dd_type:
        raise HTTPException(status_code=404, detail=f"DD type with code '{code}' not found")
    return dd_type


def get_answer_with_access(answer_id: int, db: Session, current_user: User) -> DDAnswer:
    """Load an answer and ensure the user may access its owning session.

    Raises 404 if the answer doesn't exist, 403 if the user has no access to
    the session the answer belongs to.
    """
    answer = db.query(DDAnswer).filter(DDAnswer.id == answer_id).first()
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")
    if answer.session is not None:
        assert_session_access(answer.session, current_user)
    return answer


@router.get("/by-execution/{execution_id}", response_model=list[AnswerResponse])
async def get_answers_by_execution(
    execution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get all answers for a specific execution (session + DD type combination)"""
    from app.models.execution import DDExecution

    # Verify execution exists
    execution = db.query(DDExecution).filter(DDExecution.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    # Ensure the user owns the session this execution belongs to
    if execution.session is not None:
        assert_session_access(execution.session, current_user)

    # Get all current answers for this execution
    answers = (
        db.query(DDAnswer)
        .filter(DDAnswer.execution_id == execution_id)
        .filter(DDAnswer.is_current == True)
        .order_by(DDAnswer.section_code, DDAnswer.question_code)
        .all()
    )

    # Convert to response format
    response_answers = []
    for answer in answers:
        # Handle sources field - preserve array structure for file_search sources
        sources_data = answer.sources
        if isinstance(sources_data, str):
            try:
                parsed = json.loads(sources_data) if sources_data else {}
                # Preserve arrays that contain file_search data
                if isinstance(parsed, list):
                    # Only convert to empty dict if truly empty or contains no useful data
                    if not parsed or all(
                        not item
                        or (
                            isinstance(item, dict)
                            and not any(
                                item.get(k)
                                for k in ["type", "filenames", "queries", "content", "url"]
                            )
                        )
                        for item in parsed
                    ):
                        sources_data = {}
                    else:
                        sources_data = parsed
                else:
                    sources_data = parsed
            except (json.JSONDecodeError, TypeError):
                sources_data = {}
        elif isinstance(sources_data, list):
            # Preserve arrays that contain file_search data
            if not sources_data or all(
                not item
                or (
                    isinstance(item, dict)
                    and not any(
                        item.get(k) for k in ["type", "filenames", "queries", "content", "url"]
                    )
                )
                for item in sources_data
            ):
                sources_data = {}
            # Otherwise keep the array as-is
        elif sources_data is None:
            sources_data = {}

        # Create response with fixed sources and all data
        answer_dict = answer.__dict__.copy()
        answer_dict["sources"] = sources_data

        # Add related data to dict
        answer_dict["session_name"] = execution.session.name if execution.session else None
        answer_dict["section_name"] = answer.section.title if answer.section else None
        answer_dict["question_text"] = answer.question.question_text if answer.question else None
        answer_dict["editor_name"] = answer.editor.username if answer.editor else None

        # Map answer status to validation_status for backward compatibility
        status_to_validation = {
            "approved": "approved",
            "rejected": "rejected",
            "needs_review": "pending",
            "draft": "pending",
        }
        answer_dict["validation_status"] = status_to_validation.get(answer.status.value, None)
        answer_dict["total_validations"] = (
            1 if answer.status.value in ["approved", "rejected"] else 0
        )

        # Get OpenAI message IDs from related responses
        openai_message_ids = []
        if answer.execution_id:
            from app.models.message import DDMessage
            from app.models.response import DDResponse

            message_ids = (
                db.query(DDMessage.openai_message_id)
                .join(DDResponse)
                .filter(
                    DDResponse.execution_id == answer.execution_id,
                    DDMessage.openai_message_id.isnot(None),
                )
                .all()
            )
            openai_message_ids = [mid[0] for mid in message_ids if mid[0]]
        answer_dict["openai_message_ids"] = openai_message_ids

        # Remove SQLAlchemy internal attributes
        answer_dict.pop("_sa_instance_state", None)

        answer_response = AnswerResponse(**answer_dict)

        response_answers.append(answer_response)

    return response_answers


@router.get("/all", response_model=AnswerListResponse)
async def get_all_answers(
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
    """Get all answers with advanced filtering and improved pagination"""
    # Create pagination params
    pagination_params = PaginationParams(page=page, limit=limit)

    # Build base query with eager loading to avoid N+1 queries
    from sqlalchemy.orm import joinedload

    query = db.query(DDAnswer).options(
        joinedload(DDAnswer.session),
        joinedload(DDAnswer.section),
        joinedload(DDAnswer.question),
        joinedload(DDAnswer.editor),
    )

    # Per-user isolation: restrict to answers whose session the user may access
    query = filter_sessions_for_user(
        query.join(DDSession, DDAnswer.session_id == DDSession.id), current_user
    )

    # Track applied filters
    filters = {}

    # Apply filters
    if session_id:
        query = query.filter(DDAnswer.session_id == session_id)
        filters["session_id"] = session_id

    if dd_type:
        # Get DD type by code to filter by ID
        dd_type_obj = get_dd_type_by_code(db, dd_type)
        query = query.filter(DDAnswer.dd_type_id == dd_type_obj.id)
        filters["dd_type"] = dd_type

    if status:
        query = query.filter(DDAnswer.status == status)
        filters["status"] = status

    if user_id:
        query = query.filter(DDAnswer.edited_by == user_id)
        filters["user_id"] = user_id

    if date_from:
        query = query.filter(DDAnswer.created_at >= date_from)
        filters["date_from"] = date_from

    if date_to:
        query = query.filter(DDAnswer.created_at <= date_to)
        filters["date_to"] = date_to

    if search:
        # Search in answer text and question text
        search_term = f"%{search}%"
        query = query.outerjoin(DDQuestion).filter(
            (DDAnswer.answer_text.ilike(search_term))
            | (DDQuestion.question_text.ilike(search_term))
        )
        filters["search"] = search

    # Only get current versions by default
    query = query.filter(DDAnswer.is_current == True)

    # Apply answer status filter if provided (replaces validation_status)
    if validation_status:
        # Map validation status to answer status for backward compatibility
        status_mapping = {
            "approved": "approved",
            "rejected": "rejected",
            "pending": ["needs_review", "draft"],
        }
        if validation_status in status_mapping:
            status_filter = status_mapping[validation_status]
            if isinstance(status_filter, list):
                query = query.filter(DDAnswer.status.in_(status_filter))
            else:
                query = query.filter(DDAnswer.status == status_filter)
        filters["validation_status"] = validation_status

    # Order by creation date (most recent first)
    query = query.order_by(DDAnswer.created_at.desc())

    # Get total count before pagination
    total_count = query.count()

    # Apply pagination
    paginated_query = paginate_query(query, pagination_params)
    answers = paginated_query.all()

    # Convert to response format
    response_answers = []
    for answer in answers:
        # Handle sources field - preserve array structure for file_search sources
        sources_data = answer.sources
        if isinstance(sources_data, str):
            try:
                parsed = json.loads(sources_data) if sources_data else {}
                # Preserve arrays that contain file_search data
                if isinstance(parsed, list):
                    # Only convert to empty dict if truly empty or contains no useful data
                    if not parsed or all(
                        not item
                        or (
                            isinstance(item, dict)
                            and not any(
                                item.get(k)
                                for k in ["type", "filenames", "queries", "content", "url"]
                            )
                        )
                        for item in parsed
                    ):
                        sources_data = {}
                    else:
                        sources_data = parsed
                else:
                    sources_data = parsed
            except (json.JSONDecodeError, TypeError):
                sources_data = {}
        elif isinstance(sources_data, list):
            # Preserve arrays that contain file_search data
            if not sources_data or all(
                not item
                or (
                    isinstance(item, dict)
                    and not any(
                        item.get(k) for k in ["type", "filenames", "queries", "content", "url"]
                    )
                )
                for item in sources_data
            ):
                sources_data = {}
            # Otherwise keep the array as-is
        elif sources_data is None:
            sources_data = {}

        # Create response with fixed sources and all data
        answer_dict = answer.__dict__.copy()
        answer_dict["sources"] = sources_data

        # Add related data to dict
        answer_dict["session_name"] = answer.session.name if answer.session else None
        answer_dict["section_name"] = answer.section.title if answer.section else None
        answer_dict["question_text"] = answer.question.question_text if answer.question else None
        answer_dict["editor_name"] = answer.editor.username if answer.editor else None

        # Map answer status to validation_status for backward compatibility
        status_to_validation = {
            "approved": "approved",
            "rejected": "rejected",
            "needs_review": "pending",
            "draft": "pending",
        }
        answer_dict["validation_status"] = status_to_validation.get(answer.status.value, None)
        answer_dict["total_validations"] = (
            1 if answer.status.value in ["approved", "rejected"] else 0
        )

        # Get OpenAI message IDs from related responses
        openai_message_ids = []
        if answer.execution_id:
            from app.models.message import DDMessage
            from app.models.response import DDResponse

            message_ids = (
                db.query(DDMessage.openai_message_id)
                .join(DDResponse)
                .filter(
                    DDResponse.execution_id == answer.execution_id,
                    DDMessage.openai_message_id.isnot(None),
                )
                .all()
            )
            openai_message_ids = [mid[0] for mid in message_ids if mid[0]]
        answer_dict["openai_message_ids"] = openai_message_ids

        # Remove SQLAlchemy internal attributes
        answer_dict.pop("_sa_instance_state", None)

        answer_response = AnswerResponse(**answer_dict)

        response_answers.append(answer_response)

    # Generate statistics if requested
    stats = None
    if include_stats:
        # Basic stats based on filtered results
        total_with_answers = sum(1 for a in response_answers if a.answer_text)
        total_validated = sum(1 for a in response_answers if a.validation_status == "approved")
        avg_confidence = (
            sum(a.confidence_score or 0 for a in response_answers) / len(response_answers)
            if response_answers
            else 0
        )

        stats = {
            "total_answers": len(response_answers),
            "answers_with_content": total_with_answers,
            "validated_answers": total_validated,
            "average_confidence": round(avg_confidence, 2),
            "validation_rate": round(total_validated / len(response_answers) * 100, 2)
            if response_answers
            else 0,
        }

    # Create paginated response
    meta = PaginationMeta.from_params(pagination_params, total_count)
    paginated_response = PaginatedAnswerResponse(items=response_answers, meta=meta)

    # Return formatted response with filters and stats
    return AnswerListResponse.from_paginated(paginated_response, filters=filters, stats=stats)


@router.get("/stats")
async def get_answer_statistics(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """Get answer statistics scoped to the current user's sessions"""

    def scoped():
        """Base DDAnswer query restricted to sessions the user may access."""
        q = db.query(DDAnswer)
        if not user_is_admin(current_user):
            q = filter_sessions_for_user(
                q.join(DDSession, DDAnswer.session_id == DDSession.id),
                current_user,
            )
        return q

    # Total answers
    total_answers = scoped().filter(DDAnswer.is_current == True).count()

    # By status
    status_counts = {}
    for status in AnswerStatus:
        count = scoped().filter(DDAnswer.is_current == True, DDAnswer.status == status).count()
        status_counts[status.value] = count

    # Answer status statistics
    pending_validations = (
        scoped()
        .filter(DDAnswer.is_current == True, DDAnswer.status.in_(["needs_review", "draft"]))
        .count()
    )

    validated_answers = (
        scoped().filter(DDAnswer.is_current == True, DDAnswer.status == "approved").count()
    )

    # Recent activity (last 7 days)
    from datetime import UTC, datetime, timedelta

    seven_days_ago = datetime.now(UTC) - timedelta(days=7)

    recent_answers = (
        scoped().filter(DDAnswer.created_at >= seven_days_ago, DDAnswer.is_current == True).count()
    )

    recent_edits = (
        scoped()
        .filter(
            DDAnswer.edited_at >= seven_days_ago,
            DDAnswer.edited_by.isnot(None),
            DDAnswer.is_current == True,
        )
        .count()
    )

    return {
        "total_answers": total_answers,
        "status_counts": status_counts,
        "pending_validations": pending_validations,
        "validated_answers": validated_answers,
        "recent_activity": {"new_answers": recent_answers, "recent_edits": recent_edits},
    }


@router.get("/session/{session_identifier}", response_model=AnswerListResponse)
async def get_session_answers(
    session_identifier: str,
    dd_type: str | None = None,
    section_code: str | None = None,
    execution_id: int | None = None,
    include_history: bool = False,
    page: int = 1,
    limit: int = 100,
    search: str | None = None,
    include_stats: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get all answers for a session with improved pagination and filtering"""
    # Create pagination params
    pagination_params = PaginationParams(page=page, limit=limit)

    # Handle both session ID and session code
    try:
        session_id = int(session_identifier)
        session = db.query(DDSession).filter(DDSession.id == session_id).first()
    except ValueError:
        # Not an integer, treat as session_code
        session = db.query(DDSession).filter(DDSession.session_code == session_identifier).first()
        session_id = session.id if session else None

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Per-user isolation: ensure the user may access this session
    assert_session_access(session, current_user)

    # Build query with eager loading
    from sqlalchemy.orm import joinedload

    query = (
        db.query(DDAnswer)
        .options(
            joinedload(DDAnswer.section), joinedload(DDAnswer.question), joinedload(DDAnswer.editor)
        )
        .filter(DDAnswer.session_id == session_id)
    )

    # Track applied filters
    filters = {"session_id": session_id}

    # Apply filters
    if dd_type:
        # Get DD type by code to filter by ID
        dd_type_obj = get_dd_type_by_code(db, dd_type)
        query = query.filter(DDAnswer.dd_type_id == dd_type_obj.id)
        filters["dd_type"] = dd_type

    if section_code:
        # Join with section to filter by section_code
        query = query.join(DDSection, DDAnswer.section_id == DDSection.id).filter(
            DDSection.section_code == section_code
        )
        filters["section_code"] = section_code

    if execution_id:
        query = query.filter(DDAnswer.execution_id == execution_id)
        filters["execution_id"] = execution_id

    if search:
        # Search in answer text and question text
        search_term = f"%{search}%"
        query = query.outerjoin(DDQuestion).filter(
            (DDAnswer.answer_text.ilike(search_term))
            | (DDQuestion.question_text.ilike(search_term))
        )
        filters["search"] = search

    # Only get current versions by default
    if not include_history:
        query = query.filter(DDAnswer.is_current == True)
        filters["include_history"] = include_history

    # Order by creation date
    query = query.order_by(DDAnswer.created_at)

    # Get total count before pagination
    total_count = query.count()

    # Apply pagination
    paginated_query = paginate_query(query, pagination_params)
    answers = paginated_query.all()

    # Convert to response format
    response_answers = []
    for answer in answers:
        # Handle sources field - preserve array structure for file_search sources
        sources_data = answer.sources
        if isinstance(sources_data, str):
            try:
                parsed = json.loads(sources_data) if sources_data else {}
                # Preserve arrays that contain file_search data
                if isinstance(parsed, list):
                    # Only convert to empty dict if truly empty or contains no useful data
                    if not parsed or all(
                        not item
                        or (
                            isinstance(item, dict)
                            and not any(
                                item.get(k)
                                for k in ["type", "filenames", "queries", "content", "url"]
                            )
                        )
                        for item in parsed
                    ):
                        sources_data = {}
                    else:
                        sources_data = parsed
                else:
                    sources_data = parsed
            except (json.JSONDecodeError, TypeError):
                sources_data = {}
        elif isinstance(sources_data, list):
            # Preserve arrays that contain file_search data
            if not sources_data or all(
                not item
                or (
                    isinstance(item, dict)
                    and not any(
                        item.get(k) for k in ["type", "filenames", "queries", "content", "url"]
                    )
                )
                for item in sources_data
            ):
                sources_data = {}
            # Otherwise keep the array as-is
        elif sources_data is None:
            sources_data = {}

        # Create response with fixed sources and all data
        answer_dict = answer.__dict__.copy()
        answer_dict["sources"] = sources_data

        # Add related data to dict
        answer_dict["session_name"] = session.name
        answer_dict["section_name"] = answer.section.title if answer.section else None
        answer_dict["question_text"] = answer.question.question_text if answer.question else None
        answer_dict["editor_name"] = answer.editor.username if answer.editor else None
        answer_dict["dd_type_code"] = answer.dd_type_obj.code if answer.dd_type_obj else None

        # Map answer status to validation_status for backward compatibility
        status_to_validation = {
            "approved": "approved",
            "rejected": "rejected",
            "needs_review": "pending",
            "draft": "pending",
        }
        answer_dict["validation_status"] = status_to_validation.get(answer.status.value, None)
        answer_dict["total_validations"] = (
            1 if answer.status.value in ["approved", "rejected"] else 0
        )

        # Get OpenAI message IDs from related responses
        openai_message_ids = []
        if answer.execution_id:
            from app.models.message import DDMessage
            from app.models.response import DDResponse

            message_ids = (
                db.query(DDMessage.openai_message_id)
                .join(DDResponse)
                .filter(
                    DDResponse.execution_id == answer.execution_id,
                    DDMessage.openai_message_id.isnot(None),
                )
                .all()
            )
            openai_message_ids = [mid[0] for mid in message_ids if mid[0]]
        answer_dict["openai_message_ids"] = openai_message_ids

        # Remove SQLAlchemy internal attributes
        answer_dict.pop("_sa_instance_state", None)

        answer_response = AnswerResponse(**answer_dict)

        response_answers.append(answer_response)

    # Generate statistics if requested
    stats = None
    if include_stats:
        # Session-specific stats
        total_with_answers = sum(1 for a in response_answers if a.answer_text)
        total_validated = sum(1 for a in response_answers if a.validation_status == "approved")
        avg_confidence = (
            sum(a.confidence_score or 0 for a in response_answers) / len(response_answers)
            if response_answers
            else 0
        )

        stats = {
            "session_name": session.name,
            "total_answers": len(response_answers),
            "answers_with_content": total_with_answers,
            "validated_answers": total_validated,
            "average_confidence": round(avg_confidence, 2),
            "validation_rate": round(total_validated / len(response_answers) * 100, 2)
            if response_answers
            else 0,
        }

    # Create paginated response
    meta = PaginationMeta.from_params(pagination_params, total_count)
    paginated_response = PaginatedAnswerResponse(items=response_answers, meta=meta)

    # Return formatted response with filters and stats
    return AnswerListResponse.from_paginated(paginated_response, filters=filters, stats=stats)


@router.put("/{answer_id}", response_model=AnswerResponse)
async def update_answer(
    answer_id: int,
    answer_update: AnswerUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update an answer with manual edits and version tracking"""
    answer = get_answer_with_access(answer_id, db, current_user)

    # Log sources update
    logger.info(
        f"Updating answer {answer_id}: sources type={type(answer_update.sources).__name__}, "
        f"has_sources={answer_update.sources is not None}"
    )

    # Create new history entry for the edited version
    new_history = DDAnswerHistory(
        answer_id=answer.id,
        version=answer.version + 1,
        content=answer_update.answer_text,
        sources=answer_update.sources,
        edited_by=current_user.id,
        edit_reason=answer_update.edit_reason or "Manual edit",
    )
    db.add(new_history)
    db.flush()  # Get the new history ID

    # Update answer metadata and content
    answer.version += 1
    answer.status = AnswerStatus.NEEDS_REVIEW
    answer.edited_by = current_user.id
    answer.edited_at = func.now()
    answer.answer_text = answer_update.answer_text
    # Always update sources to ensure consistency (even if None/empty)
    answer.sources = answer_update.sources

    db.commit()
    db.refresh(answer)

    return AnswerResponse.model_validate(answer)


@router.post("/{answer_id}/regenerate", response_model=AnswerResponse)
async def regenerate_answer(
    answer_id: int,
    instruction: str | None = Form(None),
    reference_url: str | None = Form(None),
    file: UploadFile | None = File(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Regenerate a single answer via the AI, reusing prior answers as context.

    The regeneration can be guided (all optional):
    - ``instruction`` : a free-text re-prompt to steer the new answer ;
    - ``reference_url`` : a URL the model is told to consult (via web_search) ;
    - ``file`` : a document added to the session vector store (reused for later
      questions) and injected into the answer's sources.

    With no guidance provided, this behaves exactly like the previous one-click
    regeneration. Creates a new version (status NEEDS_REVIEW) on the same answer
    so the version history / revert features keep working.
    """
    # Existence + per-user access (via the owning session)
    answer = get_answer_with_access(answer_id, db, current_user)

    if answer.execution is None or answer.question is None:
        raise HTTPException(
            status_code=400,
            detail="This answer cannot be regenerated (missing execution or question).",
        )

    # Resolve the DD type code, the vector stores and the company context
    from app.api.routes.processing import get_vector_store_ids_for_processing
    from app.core.cache import CacheInvalidator
    from app.engine.openai_client import OpenAIProcessor
    from app.engine.processor import DDProcessor
    from app.models.vector_store import SessionVectorStore, VectorStore

    dd_type_obj = answer.execution.dd_type
    dd_type_code = dd_type_obj.code if dd_type_obj else None
    if not dd_type_code:
        raise HTTPException(status_code=400, detail="DD type not resolvable for this answer.")

    vector_store_ids = get_vector_store_ids_for_processing(db, answer.session_id, dd_type_code)

    session = answer.session
    company = session.company if session else None
    company_info = build_company_info(company)

    # Normalize optional text inputs (empty string -> None)
    instruction = (instruction or "").strip() or None
    reference_url = (reference_url or "").strip() or None

    # Optional attached file: add it to the session vector store and keep a
    # source descriptor so it shows up in the regenerated answer's sources.
    extra_file_source = None
    if file is not None and file.filename:
        content = await read_upload(file)
        openai_processor = OpenAIProcessor()

        # Target store: an existing session/DD-type store, otherwise create one.
        store_id = vector_store_ids[0] if vector_store_ids else None
        if store_id is None:
            store_name = (
                f"{session.session_code}-regen"
                if session and getattr(session, "session_code", None)
                else f"session-{answer.session_id}-regen"
            )
            store_id = await openai_processor.create_vector_store(name=store_name)
            db.add(VectorStore(id=store_id, name=store_name, created_by=current_user.id))
            db.add(
                SessionVectorStore(
                    session_id=answer.session_id,
                    dd_type_id=dd_type_obj.id,
                    vector_store_id=store_id,
                    assigned_by=current_user.id,
                )
            )
            db.commit()
            vector_store_ids = [store_id]

        # Upload + attach (same pattern as the vector-store file endpoint)
        file_id = await openai_processor.upload_file(content, file.filename)
        await openai_processor.add_file_to_vector_store(store_id, file_id)
        CacheInvalidator.invalidate_vector_store_cache()
        # Best-effort wait for indexing so file_search can see it on first try
        await openai_processor.wait_for_file_indexed(store_id, file_id, timeout=30)

        extra_file_source = {
            "type": "file_search",
            "file_id": file_id,
            "filename": file.filename,
        }

    processor = DDProcessor(answer.session_id, dd_type_code)

    try:
        # Run the (blocking) OpenAI call off the event loop
        updated = await asyncio.to_thread(
            processor.regenerate_single_answer,
            db,
            answer,
            vector_store_ids,
            company_info,
            instruction,
            reference_url,
            extra_file_source,
        )
    except Exception:
        logger.exception("Failed to regenerate answer %s", answer_id)
        raise HTTPException(status_code=500, detail="Failed to regenerate answer")  # noqa: B904

    return AnswerResponse.model_validate(updated)


@router.patch("/{answer_id}/status", response_model=AnswerResponse)
async def update_answer_status(
    answer_id: int,
    status_update: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update answer status (NEEDS_REVIEW or APPROVED only)"""
    answer = get_answer_with_access(answer_id, db, current_user)

    new_status = status_update.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail="Status is required")

    # Only allow NEEDS_REVIEW and APPROVED statuses
    allowed_statuses = [AnswerStatus.NEEDS_REVIEW.value, AnswerStatus.APPROVED.value]
    if new_status not in allowed_statuses:
        raise HTTPException(
            status_code=400, detail=f"Status must be one of: {', '.join(allowed_statuses)}"
        )

    # Update status
    answer.status = AnswerStatus(new_status)
    answer.edited_by = current_user.id
    answer.edited_at = func.now()

    db.commit()
    db.refresh(answer)

    # Convert to response format with all fields
    sources_data = answer.sources
    if isinstance(sources_data, str):
        try:
            parsed = json.loads(sources_data) if sources_data else {}
            if isinstance(parsed, list):
                if not parsed or all(
                    not item
                    or (
                        isinstance(item, dict)
                        and not any(
                            item.get(k) for k in ["type", "filenames", "queries", "content", "url"]
                        )
                    )
                    for item in parsed
                ):
                    sources_data = {}
                else:
                    sources_data = parsed
            else:
                sources_data = parsed
        except (json.JSONDecodeError, TypeError):
            sources_data = {}
    elif isinstance(sources_data, list):
        if not sources_data or all(
            not item
            or (
                isinstance(item, dict)
                and not any(item.get(k) for k in ["type", "filenames", "queries", "content", "url"])
            )
            for item in sources_data
        ):
            sources_data = {}
    elif sources_data is None:
        sources_data = {}

    answer_dict = answer.__dict__.copy()
    answer_dict["sources"] = sources_data
    answer_dict["session_name"] = answer.session.name if answer.session else None
    answer_dict["section_name"] = answer.section.title if answer.section else None
    answer_dict["question_text"] = answer.question.question_text if answer.question else None
    answer_dict["editor_name"] = answer.editor.username if answer.editor else None

    status_to_validation = {
        "approved": "approved",
        "rejected": "rejected",
        "needs_review": "pending",
        "draft": "pending",
    }
    answer_dict["validation_status"] = status_to_validation.get(answer.status.value, None)
    answer_dict["total_validations"] = 1 if answer.status.value in ["approved", "rejected"] else 0

    openai_message_ids = []
    if answer.execution_id:
        from app.models.message import DDMessage
        from app.models.response import DDResponse

        message_ids = (
            db.query(DDMessage.openai_message_id)
            .join(DDResponse)
            .filter(
                DDResponse.execution_id == answer.execution_id,
                DDMessage.openai_message_id.isnot(None),
            )
            .all()
        )
        openai_message_ids = [mid[0] for mid in message_ids if mid[0]]
    answer_dict["openai_message_ids"] = openai_message_ids

    answer_dict.pop("_sa_instance_state", None)

    return AnswerResponse(**answer_dict)


@router.post("/{answer_id}/validate", response_model=AnswerResponse)
async def validate_answer(
    answer_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Validate/approve an answer"""
    answer = get_answer_with_access(answer_id, db, current_user)

    # Update status to approved
    answer.status = AnswerStatus.APPROVED
    answer.edited_by = current_user.id
    answer.edited_at = func.now()

    db.commit()
    db.refresh(answer)

    return AnswerResponse.model_validate(answer)


@router.post("/{answer_id}/revert", response_model=AnswerResponse)
async def revert_answer(
    answer_id: int,
    revert_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Revert an answer to a previous version"""
    answer = get_answer_with_access(answer_id, db, current_user)

    target_version = revert_data.get("version")
    if not target_version:
        raise HTTPException(status_code=400, detail="Target version is required")

    # Find the target version in history
    target_history = (
        db.query(DDAnswerHistory)
        .filter(DDAnswerHistory.answer_id == answer_id, DDAnswerHistory.version == target_version)
        .first()
    )

    if not target_history:
        raise HTTPException(status_code=404, detail=f"Version {target_version} not found")

    # Log sources revert
    logger.info(
        f"Reverting answer {answer_id} to version {target_version}: "
        f"sources type={type(target_history.sources).__name__}, "
        f"has_sources={target_history.sources is not None}"
    )

    # Create new history entry (revert is a new version)
    revert_history = DDAnswerHistory(
        answer_id=answer.id,
        version=answer.version + 1,
        content=target_history.content,
        sources=target_history.sources,
        edited_by=current_user.id,
        edit_reason=f"Reverted to version {target_version}",
    )
    db.add(revert_history)
    db.flush()

    # Update answer metadata and content
    answer.version += 1
    answer.status = AnswerStatus.NEEDS_REVIEW
    answer.edited_by = current_user.id
    answer.edited_at = func.now()
    answer.answer_text = target_history.content
    answer.sources = target_history.sources

    logger.info(
        f"Successfully reverted answer {answer_id} to version {target_version}, "
        f"new version={answer.version}, sources_restored={answer.sources is not None}"
    )

    db.commit()
    db.refresh(answer)

    return AnswerResponse.model_validate(answer)


@router.get("/{answer_id}/history", response_model=AnswerVersionHistory)
async def get_answer_history(
    answer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get version history for an answer"""
    answer = get_answer_with_access(answer_id, db, current_user)

    # Get all history entries
    history_entries = (
        db.query(DDAnswerHistory)
        .filter(DDAnswerHistory.answer_id == answer_id)
        .order_by(DDAnswerHistory.version.desc())
        .all()
    )

    # Convert to response format
    history_responses = []
    for entry in history_entries:
        history_response = AnswerHistoryResponse.model_validate(entry)
        if entry.editor:
            history_response.editor_name = entry.editor.username
        history_responses.append(history_response)

    return AnswerVersionHistory(
        answer_id=answer_id,
        current_version=answer.version,
        versions=history_responses,
        total_versions=len(history_responses),
    )


@router.get("/{answer_id}/history/{version}/raw")
async def get_raw_history(
    answer_id: int,
    version: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get raw history data for debugging (includes full sources structure)"""
    # Validates existence + per-user access to the owning session
    answer = get_answer_with_access(answer_id, db, current_user)

    history = (
        db.query(DDAnswerHistory)
        .filter(DDAnswerHistory.answer_id == answer_id, DDAnswerHistory.version == version)
        .first()
    )

    if not history:
        raise HTTPException(
            status_code=404, detail=f"History version {version} not found for answer {answer_id}"
        )

    return {
        "answer_id": answer_id,
        "requested_version": version,
        "history": {
            "version": history.version,
            "content": history.content,
            "sources": history.sources,
            "sources_type": type(history.sources).__name__,
            "sources_is_none": history.sources is None,
            "sources_count": len(history.sources)
            if isinstance(history.sources, (list, dict))
            else 0,
            "edited_by": history.edited_by,
            "edit_reason": history.edit_reason,
            "created_at": history.created_at.isoformat() if history.created_at else None,
        },
        "current_answer": {
            "version": answer.version,
            "sources": answer.sources,
            "sources_type": type(answer.sources).__name__,
            "sources_is_none": answer.sources is None,
            "sources_count": len(answer.sources) if isinstance(answer.sources, (list, dict)) else 0,
        },
    }


@router.get("/{answer_id}/with-history", response_model=AnswerWithHistory)
async def get_answer_with_history(
    answer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get an answer with its complete history and validations"""
    answer = get_answer_with_access(answer_id, db, current_user)

    # Get answer response
    answer_response = AnswerResponse.model_validate(answer)

    # Get history
    history_entries = (
        db.query(DDAnswerHistory)
        .filter(DDAnswerHistory.answer_id == answer_id)
        .order_by(DDAnswerHistory.version.desc())
        .all()
    )

    history_data = []
    for entry in history_entries:
        history_dict = {
            "id": entry.id,
            "version": entry.version,
            "content": entry.content,
            "sources": entry.sources,
            "edit_reason": entry.edit_reason,
            "editor_name": entry.editor.username if entry.editor else None,
            "created_at": entry.created_at.isoformat(),
        }
        history_data.append(history_dict)

    # Create validation data from answer status for backward compatibility
    validation_data = []
    if answer.status.value in ["approved", "rejected"]:
        validation_dict = {
            "id": answer.id,  # Use answer ID as validation ID
            "validation_status": answer.status.value,
            "comments": f"Answer {answer.status.value} via simplified workflow",
            "validator_name": answer.editor.username if answer.editor else None,
            "validated_at": answer.updated_at.isoformat()
            if answer.updated_at
            else answer.created_at.isoformat(),
        }
        validation_data.append(validation_dict)

    return AnswerWithHistory(
        answer=answer_response, history=history_data, validations=validation_data
    )


@router.get("/{answer_id}/versions/{version}", response_model=dict[str, Any])
async def get_answer_version(
    answer_id: int,
    version: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a specific version of an answer"""
    get_answer_with_access(answer_id, db, current_user)

    # Get specific version from history
    history_entry = (
        db.query(DDAnswerHistory)
        .filter(DDAnswerHistory.answer_id == answer_id, DDAnswerHistory.version == version)
        .first()
    )

    if not history_entry:
        raise HTTPException(status_code=404, detail=f"Version {version} not found")

    return {
        "answer_id": answer_id,
        "version": version,
        "content": history_entry.content,
        "sources": history_entry.sources,
        "edited_by": history_entry.editor.username if history_entry.editor else "AI System",
        "edit_reason": history_entry.edit_reason,
        "created_at": history_entry.created_at.isoformat(),
    }


@router.get("/{answer_id}/original", response_model=dict[str, Any])
async def get_original_answer(
    answer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get the original AI-generated answer (version 1)"""
    get_answer_with_access(answer_id, db, current_user)

    # Get version 1 from history (original AI answer)
    original_history = (
        db.query(DDAnswerHistory)
        .filter(DDAnswerHistory.answer_id == answer_id, DDAnswerHistory.version == 1)
        .first()
    )

    if not original_history:
        raise HTTPException(status_code=404, detail="Original answer not found")

    return {
        "answer_id": answer_id,
        "version": 1,
        "content": original_history.content,
        "sources": original_history.sources,
        "edited_by": "AI System",
        "edit_reason": original_history.edit_reason,
        "created_at": original_history.created_at.isoformat(),
        "is_original": True,
    }


@router.get("/session/{session_identifier}/export")
async def export_session_answers(
    session_identifier: str,
    format: str = "pdf",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Export session answers as PDF or Excel"""

    # Accept an id OR a session_code, like every other session route.
    # This one declared session_id: int while the sibling route just above
    # (GET /session/{session_identifier}) takes a string, and the review page is
    # reached from SessionDetail by code: FastAPI rejected the export with a 422
    # before the function was even entered. Both server-side formats failed,
    # while the CSV -- built in the browser -- kept working, which is what made
    # it look like a PDF problem.
    session, session_id = get_session_by_identifier(db, session_identifier)

    # Per-user isolation: ensure the user may access this session
    assert_session_access(session, current_user)

    # Get all answers for the session
    from app.models.dd_types import DDType

    answers = (
        db.query(DDAnswer)
        .join(DDSection, DDAnswer.section_id == DDSection.id, isouter=True)
        .join(DDQuestion, DDAnswer.question_id == DDQuestion.id, isouter=True)
        .join(DDType, DDAnswer.dd_type_id == DDType.id, isouter=True)
        .filter(DDAnswer.session_id == session_id)
        .order_by(DDType.code, DDSection.section_code, DDQuestion.question_code)
        .all()
    )

    if not answers:
        raise HTTPException(status_code=404, detail="No answers found for session")

    if format.lower() == "pdf":
        # Load any generated summaries (synthesis + per-section) for this session
        from app.models.summary import DDSummary

        summaries = db.query(DDSummary).filter(DDSummary.session_id == session_id).all()
        return AnswerExporter.generate_pdf_report(session, answers, summaries=summaries)
    elif format.lower() == "excel":
        return AnswerExporter.generate_excel_report(session, answers)
    else:
        raise HTTPException(status_code=400, detail="Format must be 'pdf' or 'excel'")


# Export functions moved to app.exports.answers for better code organization
