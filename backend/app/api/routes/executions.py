
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import case, func
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_active_user
from app.core.cache import CacheInvalidator
from app.core.database import get_db
from app.models.answer import DDAnswer
from app.models.dd_types import DDType
from app.models.execution import DDExecution, ExecutionStatus
from app.models.session import DDSession
from app.models.user import User
from app.schemas.execution import (
    ExecutionCreate,
    ExecutionResponse,
    ExecutionSummary,
    ExecutionUpdate,
    ExecutionValidate,
)
from app.services.authz import assert_session_access, filter_sessions_for_user

router = APIRouter()

# Helper function to get DD type by code
def get_dd_type_by_code(db: Session, code: str) -> DDType:
    """Helper function to get DD type by code and raise 404 if not found"""
    dd_type = db.query(DDType).filter(DDType.code == code).first()
    if not dd_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DD type with code '{code}' not found"
        )
    return dd_type


def get_execution_with_access(execution_id: int, db: Session, current_user: User) -> DDExecution:
    """Load an execution and ensure the user may access its owning session.

    Raises 404 if the execution doesn't exist, 403 if the user has no access to
    the session the execution belongs to.
    """
    execution = db.query(DDExecution).filter(DDExecution.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    if execution.session is not None:
        assert_session_access(execution.session, current_user)
    return execution


@router.get("/summary")
async def get_executions_summary(
    session_id: int | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get execution summary for answer management overview"""

    # Base query with execution and session data - updated for simplified workflow
    query = db.query(
        DDExecution,
        DDSession.name.label('session_name'),
        DDSession.company_id,
        DDType.name.label('dd_type_name'),
        DDType.description.label('dd_type_description'),
        func.count(DDAnswer.id).label('total_answers'),
        func.sum(
            case((DDAnswer.edited_by.isnot(None), 1), else_=0)
        ).label('edited_answers'),
        func.sum(
            case((DDAnswer.status == 'approved', 1), else_=0)
        ).label('approved_answers'),
        func.sum(
            case((DDAnswer.status == 'rejected', 1), else_=0)
        ).label('rejected_answers'),
        func.sum(
            case((DDAnswer.status.in_(['needs_review', 'draft', 'pending']), 1), else_=0)
        ).label('pending_answers')
    ).join(
        DDSession, DDExecution.session_id == DDSession.id
    ).join(
        DDType, DDExecution.dd_type_id == DDType.id
    ).outerjoin(
        DDAnswer, DDExecution.id == DDAnswer.execution_id
    )

    # Apply filters
    if session_id:
        query = query.filter(DDExecution.session_id == session_id)
    if status:
        query = query.filter(DDExecution.status == status)

    # Per-user isolation: restrict to sessions the user may access (query already
    # joins DDSession above)
    query = filter_sessions_for_user(query, current_user)

    # Group and order
    results = query.group_by(
        DDExecution.id,
        DDSession.name,
        DDSession.company_id,
        DDType.name,
        DDType.description
    ).order_by(
        DDSession.name,
        DDType.name
    ).all()

    # Format response
    summary_data = []
    for result in results:
        execution, session_name, company_id, dd_type_name, dd_type_description, total_answers, edited_answers, approved_answers, rejected_answers, pending_answers = result

        # Calculate review progress
        reviewed_answers = (approved_answers or 0) + (rejected_answers or 0)
        review_progress = round((reviewed_answers / total_answers * 100), 1) if total_answers else 0

        # Get dd_type_code from the relationship
        dd_type_code = execution.dd_type.code if execution.dd_type else None

        summary_data.append({
            "execution_id": execution.id,
            "session_id": execution.session_id,
            "session_name": session_name,
            "company_id": company_id,
            "dd_type_code": dd_type_code,
            "dd_type_name": dd_type_name,
            "dd_type_description": dd_type_description,
            "status": execution.status,
            "conversation_id": execution.conversation_id,
            "total_answers": total_answers or 0,
            "edited_answers": edited_answers or 0,
            "approved_answers": approved_answers or 0,
            "rejected_answers": rejected_answers or 0,
            "pending_answers": pending_answers or 0,
            "review_progress": review_progress,
            "last_updated": execution.updated_at.isoformat() if execution.updated_at else None
        })

    # Calculate summary stats
    status_counts = {}
    for item in summary_data:
        status = item["status"]
        status_counts[status] = status_counts.get(status, 0) + 1

    return {
        "executions": summary_data,
        "total_executions": len(summary_data),
        "summary_stats": {
            "by_status": status_counts,
            "total_answers": sum(item["total_answers"] for item in summary_data),
            "approved_answers": sum(item["approved_answers"] for item in summary_data),
            "rejected_answers": sum(item["rejected_answers"] for item in summary_data),
            "pending_answers": sum(item["pending_answers"] for item in summary_data)
        }
    }


@router.post("/", response_model=ExecutionResponse)
async def create_execution(
    execution: ExecutionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new DD execution for a session"""
    # Validate session exists
    session = db.query(DDSession).filter(DDSession.id == execution.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Per-user isolation: only the session owner/assignee (or admin) may create executions
    assert_session_access(session, current_user)

    # Validate DD type exists
    dd_type = db.query(DDType).filter(DDType.id == execution.dd_type_id).first()
    if not dd_type:
        raise HTTPException(status_code=404, detail="DD type not found")

    # Check if execution already exists for this session/dd_type combination
    existing = db.query(DDExecution).filter(
        DDExecution.session_id == execution.session_id,
        DDExecution.dd_type_id == execution.dd_type_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Execution already exists for session {execution.session_id} and DD type {execution.dd_type_id}"
        )

    # Create new execution
    db_execution = DDExecution(
        session_id=execution.session_id,
        dd_type_id=dd_type.id,
        status=ExecutionStatus.NOT_STARTED
    )

    db.add(db_execution)
    db.commit()
    db.refresh(db_execution)

    # Invalidate execution caches after creation
    CacheInvalidator.invalidate_execution_cache(session_id=execution.session_id)

    return ExecutionResponse.from_orm(db_execution)

@router.get("/session/{session_id}", response_model=list[ExecutionSummary])
async def get_session_executions(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all executions for a session"""
    # Validate session exists
    session = db.query(DDSession).filter(DDSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Per-user isolation: ensure the user may access this session
    assert_session_access(session, current_user)

    # Get executions with basic info (we'll calculate counts separately)
    executions = db.query(
        DDExecution,
        DDType.name.label('dd_type_name'),
        DDType.code.label('dd_type_code')
    ).join(
        DDType, DDExecution.dd_type_id == DDType.id
    ).filter(
        DDExecution.session_id == session_id
    ).all()

    result = []
    for exec_data in executions:
        execution, dd_type_name, dd_type_code = exec_data

        # Count answers separately
        total_answers = db.query(DDAnswer).filter(
            DDAnswer.execution_id == execution.id
        ).count()

        validated_answers = db.query(DDAnswer).filter(
            DDAnswer.execution_id == execution.id,
            DDAnswer.status == 'validated'
        ).count()

        pending_answers = db.query(DDAnswer).filter(
            DDAnswer.execution_id == execution.id,
            DDAnswer.status.in_(['draft', 'under_review'])
        ).count()

        result.append(ExecutionSummary(
            id=execution.id,
            dd_type_code=dd_type_code,
            dd_type_name=dd_type_name,
            status=execution.status,
            created_at=execution.created_at,
            updated_at=execution.updated_at,
            total_answers=total_answers,
            validated_answers=validated_answers,
            pending_answers=pending_answers
        ))

    return result

@router.get("/{execution_id}", response_model=ExecutionResponse)
async def get_execution(
    execution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific execution"""
    execution = db.query(DDExecution).options(
        joinedload(DDExecution.dd_type),
        joinedload(DDExecution.validator)
    ).filter(DDExecution.id == execution_id).first()

    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    # Per-user isolation: ensure the user may access this execution's session
    if execution.session is not None:
        assert_session_access(execution.session, current_user)

    # Get counts
    response_count = len(execution.responses)
    answer_count = len(execution.answers)

    response_data = ExecutionResponse.from_orm(execution)
    response_data.dd_type_name = execution.dd_type.name if execution.dd_type else None
    response_data.validator_name = execution.validator.username if execution.validator else None
    response_data.total_responses = response_count
    response_data.total_answers = answer_count

    # If execution failed (not paused), get error details from first failed answer
    if execution.status == ExecutionStatus.FAILED:  # Only for actual failures, not paused executions
        from app.models.answer import AnswerStatus
        first_failed_answer = db.query(DDAnswer).filter(
            DDAnswer.execution_id == execution_id,
            DDAnswer.status == AnswerStatus.FAILED
        ).order_by(DDAnswer.created_at.asc()).first()

        if first_failed_answer:
            response_data.failure_info = {
                "error_type": first_failed_answer.error_type.value if first_failed_answer.error_type else None,
                "error_message": first_failed_answer.error_message,
                "failed_question_code": first_failed_answer.question_code,
                "retry_count": first_failed_answer.retry_count,
                "last_error_at": first_failed_answer.last_error_at.isoformat() if first_failed_answer.last_error_at else None
            }

    return response_data

@router.put("/{execution_id}", response_model=ExecutionResponse)
async def update_execution(
    execution_id: int,
    execution_update: ExecutionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update an execution"""
    execution = get_execution_with_access(execution_id, db, current_user)

    update_data = execution_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(execution, field, value)

    db.commit()
    db.refresh(execution)

    return ExecutionResponse.from_orm(execution)

@router.post("/{execution_id}/validate")
async def validate_execution(
    execution_id: int,
    validation_request: ExecutionValidate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark an execution as validated"""
    execution = get_execution_with_access(execution_id, db, current_user)

    if execution.status != ExecutionStatus.GENERATED:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot validate execution with status: {execution.status}"
        )

    execution.status = ExecutionStatus.VALIDATED

    db.commit()

    return {"message": "Execution validated successfully", "execution_id": execution_id}

@router.post("/{execution_id}/finalize")
async def finalize_execution(
    execution_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark an execution as finalized (ready for reporting)"""
    execution = get_execution_with_access(execution_id, db, current_user)

    if execution.status != ExecutionStatus.VALIDATED:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot finalize execution with status: {execution.status}"
        )

    execution.status = ExecutionStatus.FINALIZED
    db.commit()

    return {"message": "Execution finalized successfully", "execution_id": execution_id}

@router.delete("/{execution_id}")
async def delete_execution(
    execution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete an execution and all its related data"""
    execution = get_execution_with_access(execution_id, db, current_user)

    # Check if execution can be deleted (not in progress)
    if execution.status == ExecutionStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete execution that is in progress"
        )

    db.delete(execution)
    db.commit()

    return {"message": "Execution deleted successfully", "execution_id": execution_id}
