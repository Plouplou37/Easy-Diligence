import json
import logging
import secrets
import string
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.cache import CacheInvalidator
from app.core.database import get_db
from app.core.pagination import PaginationParams, paginate_query
from app.models.company import Company
from app.models.dd_types import DDType as DDTypeModel
from app.models.questions import DDQuestion, DDSection
from app.models.session import DDSession, SessionStatus
from app.models.user import User
from app.schemas.session import (
    PaginatedSessionResponse,
    SessionCreate,
    SessionListResponse,
    SessionResponse,
    SessionStatusResponse,
)
from app.services.authz import assert_company_view

logger = logging.getLogger(__name__)

router = APIRouter()

def _cites_documents(sources) -> bool:
    """Whether an answer rests on the assigned documents, not only on the web.

    `sources` is a JSON column so it normally arrives already decoded, but some
    rows and drivers hand back the raw string -- hence the parse.
    """
    if not sources:
        return False
    if isinstance(sources, str):
        try:
            sources = json.loads(sources)
        except (ValueError, TypeError):
            return False
    return bool(isinstance(sources, dict) and sources.get("files"))


# Helper function to get DD type by code
def get_dd_type_by_code(db: Session, code: str) -> DDTypeModel:
    """Helper function to get DD type by code and raise 404 if not found"""
    dd_type = db.query(DDTypeModel).filter(DDTypeModel.code == code).first()
    if not dd_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DD type with code '{code}' not found"
        )
    return dd_type


@router.post("/", response_model=SessionResponse)
async def create_session(
    session: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new DD session"""
    # Verify company exists
    company = db.query(Company).filter(Company.id == session.company_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )

    # Per-user isolation: can only create a session on a company the user can see
    assert_company_view(company, current_user)

    # Generate unique session code
    def generate_session_code(name, user_id):
        # Take first 3 letters of session name (uppercase)
        name_part = ''.join(name.split())[:3].upper()
        if not name_part:
            name_part = 'SES'

        # Add user identifier
        user_part = str(user_id)[-2:].zfill(2)

        # Add random suffix for uniqueness
        random_part = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))

        # Combine: NAME-USER-RANDOM
        return f"{name_part}-{user_part}-{random_part}"

    session_code = generate_session_code(session.name, current_user.id)

    # Ensure uniqueness
    while db.query(DDSession).filter(DDSession.session_code == session_code).first():
        session_code = generate_session_code(session.name, current_user.id)

    # Create session with user tracking and unique code
    db_session = DDSession(
        session_code=session_code,
        company_id=session.company_id,
        name=session.name,
        description=session.description,
        status=SessionStatus.CREATED,
        created_by=current_user.id,
        assigned_to=current_user.id
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)

    # Invalidate session caches after creating new session
    CacheInvalidator.invalidate_session_cache()

    # Initialize progress for selected DD types (or all active if none specified)
    if session.dd_type_ids:
        # Use the specified DD type IDs
        selected_dd_types = db.query(DDTypeModel).filter(
            DDTypeModel.id.in_(session.dd_type_ids),
            DDTypeModel.is_active == True
        ).all()
    else:
        # Default: all active DD types
        selected_dd_types = db.query(DDTypeModel).filter(DDTypeModel.is_active == True).all()

    for dd_type in selected_dd_types:
        # Get sections directly from the DD type (consolidated structure)
        sections = db.query(DDSection).filter(DDSection.dd_type_id == dd_type.id).all()

        total_questions = 0
        if sections:
            # Count all questions in all sections of this DD type
            for section in sections:
                questions_count = db.query(DDQuestion).filter(DDQuestion.section_id == section.id).count()
                total_questions += questions_count

            # Progress tracking is handled by dd_executions table
        else:
            # No sections found for this DD type - continue
            pass

    # Store the selected DD types in the session for frontend reference
    if selected_dd_types:
        dd_types_data = [{"code": dd_type.code, "name": dd_type.name} for dd_type in selected_dd_types]
        db_session.dd_types_json = json.dumps(dd_types_data)

    db.commit()
    return db_session

@router.get("/{session_identifier}", response_model=SessionResponse)
async def get_session(
    session_identifier: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific session by ID or code - check user permissions"""
    # Try to parse as integer ID first
    try:
        session_id = int(session_identifier)
        session = db.query(DDSession).filter(DDSession.id == session_id).first()
    except ValueError:
        # Not an integer, treat as session_code
        session = db.query(DDSession).filter(DDSession.session_code == session_identifier).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Check permissions: admin can see all, others only their own
    if current_user.role != "admin":
        if session.created_by != current_user.id and session.assigned_to != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this session"
            )

    # Use custom serialization to ensure dd_types_json is included
    return SessionResponse.from_db_model(session)

@router.get("/{session_identifier}/status", response_model=SessionStatusResponse)
async def get_session_status(
    session_identifier: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get session status with progress for all DD types - check permissions"""
    # Try to parse as integer ID first
    try:
        session_id = int(session_identifier)
        session = db.query(DDSession).filter(DDSession.id == session_id).first()
    except ValueError:
        # Not an integer, treat as session_code
        session = db.query(DDSession).filter(DDSession.session_code == session_identifier).first()
        session_id = session.id if session else None
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Check permissions
    if current_user.role != "admin":
        if session.created_by != current_user.id and session.assigned_to != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this session"
            )

    # Get executions with preloaded relationships for efficiency
    from sqlalchemy.orm import joinedload

    from app.models.execution import DDExecution
    execution_records = db.query(DDExecution).options(
        joinedload(DDExecution.dd_type)
    ).filter(
        DDExecution.session_id == session.id
    ).all()

    # If no executions, return empty progress (new sessions won't have progress until executions are created)
    if not execution_records:
        return SessionStatusResponse(
            id=session.id,
            status=session.status,
            progress=[]
        )

    # Optimize: Get all answer statistics in one query instead of N separate queries
    from sqlalchemy import case, distinct, func

    from app.models.answer import AnswerStatus, DDAnswer

    # Get answer statistics for all executions in one query
    answer_stats = db.query(
        DDAnswer.execution_id,
        func.count(distinct(
            case(
                (DDAnswer.answer_text.isnot(None), DDAnswer.question_id),
                else_=None
            )
        )).label('questions_answered'),
        func.count(distinct(
            case(
                (DDAnswer.status == AnswerStatus.COMPLETED, DDAnswer.question_id),
                else_=None
            )
        )).label('questions_completed')
    ).filter(
        DDAnswer.execution_id.in_([ex.id for ex in execution_records])
    ).group_by(DDAnswer.execution_id).all()

    # Create a lookup dict for answer stats
    stats_lookup = {
        stats.execution_id: {
            'answered': stats.questions_answered,
            'completed': stats.questions_completed
        }
        for stats in answer_stats
    }

    progress_data = []
    for execution in execution_records:
        # Get DD type info from preloaded relationship
        dd_type_code = execution.dd_type.code if execution.dd_type else None
        dd_type_name = execution.dd_type.name if execution.dd_type else None

        # Get answer statistics from our optimized lookup
        execution_stats = stats_lookup.get(execution.id, {'answered': 0, 'completed': 0})
        unique_questions_answered = execution_stats['answered']

        # Map execution status to UI progress status
        if execution.status == "not_started":
            ui_status = "not_started"
            questions_processed = 0
        elif execution.status == "in_progress":
            ui_status = "in_progress"
            questions_processed = unique_questions_answered  # Unique questions answered
        elif execution.status == "generated":
            ui_status = "completed"  # Processing complete from UI perspective
            questions_processed = unique_questions_answered  # Unique questions answered
        elif execution.status == "failed":
            ui_status = "failed"  # Show failed status in UI
            questions_processed = unique_questions_answered  # Show how many succeeded before failure
        elif execution.status == "paused":
            ui_status = "paused"  # Show paused status in UI
            questions_processed = unique_questions_answered  # Show progress made before pause
        else:
            ui_status = execution.status
            questions_processed = unique_questions_answered

        # Get total questions for this DD type (not just answered ones)
        from app.models.questions import DDQuestion, DDSection
        total_questions_in_type = db.query(DDQuestion).join(DDSection).filter(
            DDSection.dd_type_id == execution.dd_type_id
        ).count()

        # Calculate percentage
        percentage = (questions_processed / total_questions_in_type * 100) if total_questions_in_type > 0 else 0

        # Get sections progress data for this DD type
        sections_progress = []
        sections = db.query(DDSection).filter(
            DDSection.dd_type_id == execution.dd_type_id
        ).order_by(DDSection.order_index).all()

        # Optimize: Get section statistics in batch queries instead of per-section
        section_question_counts = {}
        section_answer_counts = {}

        if sections:
            # Get all question counts for all sections in one query
            section_counts_query = db.query(
                DDQuestion.section_id,
                func.count(DDQuestion.id).label('total_questions')
            ).filter(
                DDQuestion.section_id.in_([s.id for s in sections])
            ).group_by(DDQuestion.section_id).all()

            section_question_counts = {
                row.section_id: row.total_questions
                for row in section_counts_query
            }

            # Get all answered questions counts for this execution in one query
            section_answer_query = db.query(
                DDQuestion.section_id,
                func.count(distinct(DDAnswer.question_id)).label('answered_questions')
            ).join(DDAnswer).filter(
                DDAnswer.execution_id == execution.id,
                DDQuestion.section_id.in_([s.id for s in sections]),
                DDAnswer.answer_text.isnot(None)
            ).group_by(DDQuestion.section_id).all()

            section_answer_counts = {
                row.section_id: row.answered_questions
                for row in section_answer_query
            }

        for section in sections:
            # Get counts from our optimized batch queries
            section_total_questions = section_question_counts.get(section.id, 0)
            section_questions_answered = section_answer_counts.get(section.id, 0)

            section_percentage = (section_questions_answered / section_total_questions * 100) if section_total_questions > 0 else 0

            # Determine section status
            if section_questions_answered == 0:
                section_status = "not_started"
            elif section_questions_answered == section_total_questions:
                section_status = "completed"
            else:
                section_status = "in_progress"

            sections_progress.append({
                "name": section.title,
                "status": section_status,
                "questions_completed": section_questions_answered,
                "total_questions": section_total_questions,
                "percentage": section_percentage
            })

        # Get analytics data from answers. Only the current version of each:
        # superseded versions and failed retries stay in the table, and counting
        # their tokens inflated the total well past what the run actually cost.
        answers = db.query(DDAnswer).filter(
            DDAnswer.execution_id == execution.id,
            DDAnswer.is_current == True  # noqa: E712 -- SQL comparison, not Python
        ).all()

        tokens_used = 0
        answers_with_documents = 0
        answer_times = []
        for answer in answers:
            if answer.tokens_used:
                tokens_used += answer.tokens_used
            if _cites_documents(answer.sources):
                answers_with_documents += 1
            if answer.created_at:
                answer_times.append(answer.created_at)

        # Time actually spent answering, measured on the answers themselves.
        # It used to be execution.updated_at - created_at, but that row is only
        # written at the start and at the end of a run: the value stayed at 0
        # for the whole run ("Starting..." on screen) and then jumped to the
        # total -- and on a resumed execution it counted the idle hours too.
        time_elapsed = 0
        if answer_times:
            first = min(answer_times)
            if execution.status == "in_progress":
                now = datetime.now(first.tzinfo) if first.tzinfo else datetime.now()
                time_elapsed = int((now - first).total_seconds())
            else:
                time_elapsed = int((max(answer_times) - first).total_seconds())

        # If execution failed (not paused), get error details from first failed answer
        last_error = None
        if execution.status == "failed":  # Only for actual failures, not paused executions
            first_failed_answer = db.query(DDAnswer).filter(
                DDAnswer.execution_id == execution.id,
                DDAnswer.status == AnswerStatus.FAILED
            ).order_by(DDAnswer.created_at.asc()).first()

            if first_failed_answer and first_failed_answer.error_message:
                error_type_str = first_failed_answer.error_type.value if first_failed_answer.error_type else "unknown"
                last_error = f"{error_type_str}: {first_failed_answer.error_message}"

        progress_data.append({
            "dd_type": dd_type_code,
            "dd_type_name": dd_type_name,
            "status": ui_status,
            "questions_completed": questions_processed,
            "total_questions": total_questions_in_type,
            "percentage": percentage,
            "sections_progress": sections_progress,
            "tokens_used": tokens_used,
            # How many answers actually rest on the assigned documents. Replaces
            # average_confidence, whose source stopped being written when the
            # hardcoded 0.8 was removed -- it could only ever show "N/A".
            "answers_with_documents": answers_with_documents,
            "answers_counted": len(answers),
            "time_elapsed": time_elapsed,
            "current_section": None,  # Not tracked in new system
            "current_question": None,  # Not tracked in new system
            "last_error": last_error,  # Error message when status is failed
        })

    return SessionStatusResponse(
        id=session.id,
        status=session.status,
        progress=progress_data
    )

@router.get("/", response_model=SessionListResponse)
async def list_sessions(
    company_id: int | None = None,
    page: int = 1,
    limit: int = 50,
    status: str | None = None,
    created_by: int | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List sessions with improved pagination and filtering"""
    # Create pagination params
    pagination_params = PaginationParams(page=page, limit=limit)

    # Build base query
    query = db.query(DDSession)

    # Apply filters
    filters = {}

    # User permission filter
    if current_user.role != "admin":
        query = query.filter(
            (DDSession.created_by == current_user.id) |
            (DDSession.assigned_to == current_user.id)
        )

    if company_id:
        query = query.filter(DDSession.company_id == company_id)
        filters["company_id"] = company_id

    if status:
        from app.models.session import SessionStatus
        query = query.filter(DDSession.status == SessionStatus(status))
        filters["status"] = status

    if created_by:
        query = query.filter(DDSession.created_by == created_by)
        filters["created_by"] = created_by

    if search:
        # Search in session name and description
        search_term = f"%{search}%"
        query = query.filter(
            (DDSession.name.ilike(search_term)) |
            (DDSession.description.ilike(search_term))
        )
        filters["search"] = search

    # Add eager loading for related data to avoid N+1 queries
    from sqlalchemy.orm import joinedload
    query = query.options(
        joinedload(DDSession.company),
        joinedload(DDSession.creator),
        joinedload(DDSession.assignee)
    )

    # Order by creation date (most recent first)
    query = query.order_by(DDSession.created_at.desc())

    # Get total count before pagination
    total_count = query.count()

    # Apply pagination
    paginated_query = paginate_query(query, pagination_params)
    sessions = paginated_query.all()

    # Convert to response objects
    session_responses = []
    for session in sessions:
        # Use custom serialization method
        session_response = SessionResponse.from_db_model(session)

        # Add username if available from preloaded relationship
        if session.creator:
            session_response.created_by_username = session.creator.username or session.creator.email

        session_responses.append(session_response)

    # Create paginated response
    from app.core.pagination import PaginationMeta
    meta = PaginationMeta.from_params(pagination_params, total_count)
    paginated_response = PaginatedSessionResponse(items=session_responses, meta=meta)

    # Return formatted response with filters
    return SessionListResponse.from_paginated(paginated_response, filters=filters)

@router.delete("/{session_identifier}")
async def delete_session(
    session_identifier: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a session - only allowed for sessions not in progress or completed"""
    # Try to parse as integer ID first
    try:
        session_id = int(session_identifier)
        session = db.query(DDSession).filter(DDSession.id == session_id).first()
    except ValueError:
        # Not an integer, treat as session_code
        session = db.query(DDSession).filter(DDSession.session_code == session_identifier).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Check permissions: only creator can delete (even admins must be the creator)
    if session.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the session creator can delete this session"
        )

    # Prevent deletion of sessions in progress or completed
    if session.status in [SessionStatus.IN_PROGRESS, SessionStatus.COMPLETED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete session with status '{session.status.value}'. Only sessions with status 'created', 'documents_uploaded', 'failed', or 'paused' can be deleted."
        )

    # Delete the session - CASCADE will handle related records
    # (dd_answers, dd_executions, session_vector_stores, and their children)
    db.delete(session)
    db.commit()

    # Invalidate session caches after deletion
    CacheInvalidator.invalidate_session_cache()

    return {
        "message": "Session deleted successfully",
        "session_id": session.id,
        "session_code": session.session_code
    }
