from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.session import DDSession
from app.models.company import Company
from app.models.execution import DDExecution, ExecutionStatus
from app.models.vector_store import SessionVectorStore
from app.models.user import User
from app.engine.processor import DDProcessor
from app.core.utils import get_session_by_identifier, build_company_info
from app.services.authz import assert_session_access
from app.api.deps import get_current_active_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Background task wrapper to catch and log exceptions
def safe_background_task(func, session_id, dd_type, *args, **kwargs):
    """Wrapper to catch background task exceptions and update execution status"""
    try:
        logger.info(f"Starting background task: {func.__name__} for session={session_id}, dd_type={dd_type}")
        result = func(*args, **kwargs)
        logger.info(f"Background task completed successfully: {func.__name__}")
        return result
    except Exception as e:
        logger.error(f"Background task failed: {func.__name__} for session={session_id}, dd_type={dd_type}")
        logger.error(f"Error: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")

        # Update execution status to FAILED
        try:
            from app.core.database import SessionLocal
            db = SessionLocal()
            try:
                # Get DD type by code
                from app.models.dd_types import DDType
                dd_type_obj = db.query(DDType).filter(DDType.code == dd_type).first()
                if dd_type_obj:
                    execution = db.query(DDExecution).filter(
                        DDExecution.session_id == session_id,
                        DDExecution.dd_type_id == dd_type_obj.id
                    ).first()
                    if execution:
                        execution.status = ExecutionStatus.FAILED
                        db.commit()
                        logger.info(f"Updated execution {execution.id} status to FAILED")
            finally:
                db.close()
        except Exception as status_error:
            logger.error(f"Failed to update execution status: {status_error}")

        raise

# Helper function to get DD type by code
def get_dd_type_by_code(db: Session, code: str):
    """Helper function to get DD type by code"""
    from app.models.dd_types import DDType
    dd_type = db.query(DDType).filter(DDType.code == code).first()
    if not dd_type:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"DD type with code '{code}' not found")
    return dd_type

def get_vector_store_ids_for_processing(db: Session, session_id: int, dd_type: str) -> list[str]:
    """Get vector store IDs for a specific session and DD type.

    Priority:
    1. DD-type specific assignments
    2. Session-level assignments (all DD types)
    """
    vector_store_ids = []

    # Get DD type by code to get its ID
    dd_type_obj = get_dd_type_by_code(db, dd_type)

    # Check for DD-type specific assignments
    dd_assignments = db.query(SessionVectorStore).filter(
        SessionVectorStore.session_id == session_id,
        SessionVectorStore.dd_type_id == dd_type_obj.id
    ).all()
    
    if dd_assignments:
        vector_store_ids = [assignment.vector_store_id for assignment in dd_assignments]
    else:
        # Check for session-level assignments (all DD types)
        session_assignments = db.query(SessionVectorStore).filter(
            SessionVectorStore.session_id == session_id,
            SessionVectorStore.dd_type_id.is_(None)  # NULL means all DD types
        ).all()
        
        if session_assignments:
            vector_store_ids = [assignment.vector_store_id for assignment in session_assignments]
    
    return vector_store_ids

@router.post("/session/{session_identifier}/dd/{dd_type}/start")
async def start_dd_processing(
    session_identifier: str,
    dd_type: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Start DD processing for a specific type"""
    session, session_id = get_session_by_identifier(db, session_identifier)
    assert_session_access(session, current_user)

    # Get company info
    company = db.query(Company).filter(Company.id == session.company_id).first()
    company_info = build_company_info(company)
    
    # Get DD type by code to get its ID
    dd_type_obj = get_dd_type_by_code(db, dd_type)

    # Get vector store IDs using new assignment system
    vector_store_ids = get_vector_store_ids_for_processing(db, session_id, dd_type)

    # Check if execution exists
    execution = db.query(DDExecution).filter(
        DDExecution.session_id == session_id,
        DDExecution.dd_type_id == dd_type_obj.id
    ).first()

    # If execution exists, check its status
    if execution:
        # If already completed or validated, don't restart (user should use resume for continuation)
        # ISSUE #13 FIX: Added GENERATED to prevent overwriting completed executions
        if execution.status in [ExecutionStatus.VALIDATED, ExecutionStatus.FINALIZED, ExecutionStatus.GENERATED]:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": f"Execution already {execution.status}. Cannot restart.",
                    "execution_id": execution.id,
                    "status": execution.status,
                    "hint": "This execution is complete. Create a new session to start fresh, or use Resume to fix failed questions."
                }
            )

        # For IN_PROGRESS, check if it might be stuck (updated more than 10 minutes ago)
        from datetime import datetime, timedelta
        if execution.status == ExecutionStatus.IN_PROGRESS:
            time_since_update = datetime.now(execution.updated_at.tzinfo) - execution.updated_at
            if time_since_update > timedelta(minutes=10):
                logger.warning(f"Execution {execution.id} appears stuck (last update: {execution.updated_at}). Allowing restart via resume.")
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Execution appears stuck",
                        "execution_id": execution.id,
                        "status": execution.status,
                        "hint": "Use the Resume button instead to continue from where it left off."
                    }
                )
            else:
                # Actually still running
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "DD processing already in progress",
                        "execution_id": execution.id,
                        "status": execution.status
                    }
                )

        # For FAILED, GENERATED, or NOT_STARTED, we allow restarting
        logger.info(f"Restarting execution {execution.id} with status {execution.status} for session {session_id}, DD type {dd_type}")
        execution.status = ExecutionStatus.IN_PROGRESS
        db.commit()
    else:
        # Create new execution record
        execution = DDExecution(
            session_id=session_id,
            dd_type_id=dd_type_obj.id,
            status=ExecutionStatus.IN_PROGRESS.value
        )
        db.add(execution)
        db.commit()
        db.refresh(execution)
        logger.info(f"Created new execution {execution.id} for session {session_id}, DD type {dd_type}")
    
    # Start processing in background with error handling
    processor = DDProcessor(session_id, dd_type)
    background_tasks.add_task(
        safe_background_task,
        processor.start_processing,
        session_id,
        dd_type,
        vector_store_ids,
        company_info
    )
    
    return {
        "message": f"Started {dd_type} processing", 
        "session_id": session_id,
        "execution_id": execution.id
    }

@router.post("/session/{session_identifier}/dd/{dd_type}/pause")
async def pause_dd_processing(
    session_identifier: str,
    dd_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Pause/cancel DD processing for a specific type"""
    session, session_id = get_session_by_identifier(db, session_identifier)
    assert_session_access(session, current_user)

    # Get DD type by code to get its ID
    dd_type_obj = get_dd_type_by_code(db, dd_type)

    # Check execution status
    execution = db.query(DDExecution).filter(
        DDExecution.session_id == session_id,
        DDExecution.dd_type_id == dd_type_obj.id
    ).first()

    if not execution:
        raise HTTPException(
            status_code=404,
            detail="No execution record found"
        )

    # Only allow pausing if in progress
    if execution.status != ExecutionStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot pause execution with status {execution.status}"
        )

    # Mark as paused
    execution.status = ExecutionStatus.PAUSED
    db.commit()

    logger.info(f"Paused execution {execution.id} for session {session_id}, DD type {dd_type}")

    return {
        "message": f"Paused {dd_type} processing",
        "session_id": session_id,
        "execution_id": execution.id,
        "status": execution.status
    }

@router.post("/session/{session_identifier}/dd/{dd_type}/resume")
async def resume_dd_processing(
    session_identifier: str,
    dd_type: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Resume DD processing from failure point"""
    logger.info(f"RESUME ENDPOINT: Received resume request for session={session_identifier}, dd_type={dd_type}")
    session, session_id = get_session_by_identifier(db, session_identifier)
    assert_session_access(session, current_user)

    # Get DD type by code to get its ID
    dd_type_obj = get_dd_type_by_code(db, dd_type)

    # Check execution status
    execution = db.query(DDExecution).filter(
        DDExecution.session_id == session_id,
        DDExecution.dd_type_id == dd_type_obj.id
    ).first()

    if not execution:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "No execution record found",
                "session_id": session_id,
                "dd_type": dd_type
            }
        )

    # Check if we can resume - Allow resuming stuck IN_PROGRESS executions
    resumable_statuses = [ExecutionStatus.NOT_STARTED, ExecutionStatus.IN_PROGRESS, ExecutionStatus.GENERATED, ExecutionStatus.FAILED, ExecutionStatus.PAUSED]
    if execution.status not in resumable_statuses:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Cannot resume execution",
                "current_status": execution.status,
                "resumable_statuses": [status.value for status in resumable_statuses],
                "execution_id": execution.id
            }
        )

    # Get session and company info
    session = db.query(DDSession).filter(DDSession.id == session_id).first()
    company = db.query(Company).filter(Company.id == session.company_id).first()
    company_info = build_company_info(company)

    # Get vector store IDs using new assignment system
    vector_store_ids = get_vector_store_ids_for_processing(db, session_id, dd_type)

    # Resume processing using the new resume method with error handling
    processor = DDProcessor(session_id, dd_type)
    logger.info(f"RESUME ENDPOINT: Adding background task for resume_processing")
    background_tasks.add_task(
        safe_background_task,
        processor.resume_processing,
        session_id,
        dd_type,
        vector_store_ids,
        company_info
    )
    logger.info(f"RESUME ENDPOINT: Background task added, returning response")

    return {
        "message": f"Resumed {dd_type} processing",
        "session_id": session_id,
        "execution_id": execution.id if execution else None
    }

@router.get("/session/{session_identifier}/dd/{dd_type}/progress")
async def get_dd_progress(
    session_identifier: str,
    dd_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get progress for a specific DD type"""
    session, session_id = get_session_by_identifier(db, session_identifier)
    assert_session_access(session, current_user)

    # Get DD type by code to get its ID
    dd_type_obj = get_dd_type_by_code(db, dd_type)

    # Check for execution first (new system)
    execution = db.query(DDExecution).filter(
        DDExecution.session_id == session_id,
        DDExecution.dd_type_id == dd_type_obj.id
    ).first()
    
    if execution:
        # Use execution-based progress
        return {
            "dd_type": dd_type,
            "status": execution.status,
            "execution_id": execution.id,
            "created_at": execution.created_at,
            "updated_at": execution.updated_at,
            "conversation_id": execution.conversation_id
        }
    
    # No execution found - this DD type hasn't been started yet
    raise HTTPException(status_code=404, detail="No execution record found for this DD type")