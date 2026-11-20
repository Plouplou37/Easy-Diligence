"""Running a DD type on a session: start, pause, resume, progress.

A run goes on in a background task after the response; the page follows it
through the session status.
"""

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_accessible_session, get_visible_dd_type
from app.core.database import get_db
from app.engine.processor import DDProcessor
from app.models.base import stored_id
from app.models.dd_types import DDType
from app.models.execution import DDExecution
from app.models.session import DDSession
from app.services import processing

router = APIRouter()

RUN = "/session/{session_identifier}/dd/{dd_type}"


def _schedule(
    background_tasks: BackgroundTasks,
    db: Session,
    session: DDSession,
    dd_type: DDType,
    execution: DDExecution,
    resume: bool,
) -> None:
    context = processing.run_context(db, session, dd_type)
    processor = DDProcessor(stored_id(execution), stored_id(dd_type), dd_type.code)
    run = processor.resume_processing if resume else processor.start_processing
    background_tasks.add_task(
        processing.run_in_background,
        run,
        stored_id(session),
        stored_id(dd_type),
        context["vector_store_ids"],
        context["company_info"],
    )


@router.post(RUN + "/start")
def start_dd_processing(
    background_tasks: BackgroundTasks,
    session: DDSession = Depends(get_accessible_session),
    dd_type: DDType = Depends(get_visible_dd_type),
    db: Session = Depends(get_db),
):
    """Start answering every question of a DD type."""
    execution = processing.start(db, session, dd_type)
    _schedule(background_tasks, db, session, dd_type, execution, resume=False)
    return {
        "message": f"Started {dd_type.code} processing",
        "session_id": session.id,
        "execution_id": execution.id,
    }


@router.post(RUN + "/pause")
def pause_dd_processing(
    session: DDSession = Depends(get_accessible_session),
    dd_type: DDType = Depends(get_visible_dd_type),
    db: Session = Depends(get_db),
):
    """Stop a run after the question it is on."""
    execution = processing.pause(db, session, dd_type)
    return {
        "message": f"Paused {dd_type.code} processing",
        "session_id": session.id,
        "execution_id": execution.id,
        "status": execution.status,
    }


@router.post(RUN + "/resume")
def resume_dd_processing(
    background_tasks: BackgroundTasks,
    session: DDSession = Depends(get_accessible_session),
    dd_type: DDType = Depends(get_visible_dd_type),
    db: Session = Depends(get_db),
):
    """Go on with a run: unanswered and failed questions, same conversation."""
    execution = processing.resume(db, session, dd_type)
    _schedule(background_tasks, db, session, dd_type, execution, resume=True)
    return {
        "message": f"Resumed {dd_type.code} processing",
        "session_id": session.id,
        "execution_id": execution.id,
    }


@router.get(RUN + "/progress")
def get_dd_progress(
    session: DDSession = Depends(get_accessible_session),
    dd_type: DDType = Depends(get_visible_dd_type),
    db: Session = Depends(get_db),
):
    """The state of a DD type run."""
    execution = processing.get_execution(db, stored_id(session), stored_id(dd_type))
    return {
        "dd_type": dd_type.code,
        "status": execution.status,
        "execution_id": execution.id,
        "created_at": execution.created_at,
        "updated_at": execution.updated_at,
        "conversation_id": execution.conversation_id,
    }
