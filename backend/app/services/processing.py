"""Running a DD type on a session: start, pause, resume, and the background run.

The answering itself is the engine's (engine/processor.py). This module decides
whether a run may start or resume, gathers what the engine needs (the vector
stores, the company described to the model), and keeps the execution status
right when the background run crashes.

Each change of status is one conditional UPDATE (`_switch`), never a read then
a write: of two clicks, or two tabs, only one gets the run.
"""

import logging
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any, NoReturn

from sqlalchemy import and_, exists, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import col

from app.core import database
from app.core.exceptions import InvalidRequestError, NotFoundError
from app.models.answer import DDAnswer
from app.models.base import stored_id
from app.models.company import Company
from app.models.dd_types import DDType
from app.models.execution import DDExecution, ExecutionStatus
from app.models.session import DDSession
from app.models.vector_store import SessionVectorStore

logger = logging.getLogger(__name__)

# A run in progress that has written no answer, nor changed its execution, for
# this long is considered stuck: Resume may take it over.
STUCK_AFTER = timedelta(minutes=10)

# Statuses a run may be started from: neither running nor finished.
_STARTABLE = (
    ExecutionStatus.NOT_STARTED,
    ExecutionStatus.FAILED,
    ExecutionStatus.PAUSED,
    ExecutionStatus.UNDER_REVIEW,
)
_FINISHED = (ExecutionStatus.GENERATED, ExecutionStatus.VALIDATED, ExecutionStatus.FINALIZED)

# Statuses a run may be resumed from (besides a stuck run): all but the
# validated ones and a run going on.
_RESUMABLE = (
    ExecutionStatus.NOT_STARTED,
    ExecutionStatus.GENERATED,
    ExecutionStatus.FAILED,
    ExecutionStatus.PAUSED,
)


def build_company_info(company: Company | None) -> dict[str, Any]:
    """Context describing the DD subject, as handed to the model.

    Carries the fund AND its management company as two distinct entities: the
    questionnaires ask about both, and without the distinction the model -- and
    the web search behind it -- has to guess which one a question targets.

    The one source for start, resume and regenerate, so a new field reaches all
    of them at once. {} without a company, which the system prompt handles.
    """
    if company is None:
        return {}
    return {
        "name": company.name,
        "website_url": company.website_url,
        "description": company.description,
        "management_company_name": company.management_company_name,
        "management_company_website": company.management_company_website,
    }


def vector_store_ids_for(db: Session, session_id: int, dd_type_id: int) -> list[str]:
    """The vector stores a run searches: those assigned to this DD type of the
    session, or else those assigned to the whole session."""
    by_scope = db.query(col(SessionVectorStore.vector_store_id)).filter(
        col(SessionVectorStore.session_id) == session_id
    )
    for_this_type = by_scope.filter(col(SessionVectorStore.dd_type_id) == dd_type_id).all()
    if for_this_type:
        return [row[0] for row in for_this_type]
    return [row[0] for row in by_scope.filter(col(SessionVectorStore.dd_type_id).is_(None)).all()]


def find_execution(db: Session, session_id: int, dd_type_id: int) -> DDExecution | None:
    return (
        db.query(DDExecution)
        .filter(
            col(DDExecution.session_id) == session_id,
            col(DDExecution.dd_type_id) == dd_type_id,
        )
        .first()
    )


def get_execution(db: Session, session_id: int, dd_type_id: int) -> DDExecution:
    execution = find_execution(db, session_id, dd_type_id)
    if execution is None:
        raise NotFoundError("No execution record found for this DD type")
    return execution


def run_context(db: Session, session: DDSession, dd_type: DDType) -> dict[str, Any]:
    """What the engine needs for a run: its vector stores and the company."""
    return {
        "vector_store_ids": vector_store_ids_for(db, stored_id(session), stored_id(dd_type)),
        "company_info": build_company_info(db.get(Company, session.company_id)),
    }


def _stuck(execution_id: int) -> ColumnElement[bool]:
    """The run is in progress, but neither it nor its answers have moved for
    STUCK_AFTER. The execution row alone would not do: the engine only touches
    it at the start and the end of a run, which may last more than an hour."""
    since = datetime.now(UTC) - STUCK_AFTER
    recent_answer = exists(
        select(col(DDAnswer.id)).where(
            col(DDAnswer.execution_id) == execution_id, col(DDAnswer.created_at) >= since
        )
    )
    return and_(
        col(DDExecution.status) == ExecutionStatus.IN_PROGRESS,
        col(DDExecution.updated_at) < since,
        ~recent_answer,
    )


def _is_stuck(db: Session, execution: DDExecution) -> bool:
    execution_id = stored_id(execution)
    query = select(col(DDExecution.id)).where(
        col(DDExecution.id) == execution_id, _stuck(execution_id)
    )
    return db.execute(query).first() is not None


def _switch(
    db: Session,
    execution: DDExecution,
    to: ExecutionStatus,
    allowed: Sequence[ExecutionStatus],
    *,
    or_stuck: bool = False,
) -> bool:
    """Set the status to `to` if it is still one of `allowed` (or the run is
    stuck), in one conditional UPDATE. False when another request changed it
    first; the execution is reloaded either way."""
    execution_id = stored_id(execution)
    condition: ColumnElement[bool] = col(DDExecution.status).in_(allowed)
    if or_stuck:
        condition = or_(condition, _stuck(execution_id))
    result = db.execute(
        update(DDExecution)
        .where(col(DDExecution.id) == execution_id, condition)
        .values(status=to)
        .execution_options(synchronize_session=False)
    )
    db.commit()
    db.refresh(execution)
    return result.rowcount == 1


def _create_running(db: Session, session: DDSession, dd_type: DDType) -> DDExecution | None:
    """A new execution, in progress; None if a concurrent start created it
    first (one execution per session and DD type)."""
    execution = DDExecution(
        session_id=stored_id(session),
        dd_type_id=stored_id(dd_type),
        status=ExecutionStatus.IN_PROGRESS,
    )
    db.add(execution)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return None
    db.refresh(execution)
    logger.info(
        "Created execution %s for session %s, DD type %s",
        execution.id,
        session.id,
        dd_type.code,
    )
    return execution


def _refuse_start(db: Session, execution: DDExecution) -> NoReturn:
    status = execution.status
    if status in _FINISHED:
        raise InvalidRequestError(
            f"Execution already {status.value}: it cannot be restarted. "
            "Use Resume to retry failed questions, or create a new session."
        )
    if status == ExecutionStatus.IN_PROGRESS and _is_stuck(db, execution):
        logger.warning("Execution %s looks stuck", execution.id)
        raise InvalidRequestError(
            "This run looks stuck. Use Resume to continue from where it stopped."
        )
    raise InvalidRequestError("DD processing already in progress")


def start(db: Session, session: DDSession, dd_type: DDType) -> DDExecution:
    """Mark the run in progress, creating its execution on first start.

    A finished run is not restarted (resume retries its failed questions), nor
    is one already running.
    """
    execution = find_execution(db, stored_id(session), stored_id(dd_type))
    if execution is None:
        created = _create_running(db, session, dd_type)
        if created is not None:
            return created
        # Another start created it meanwhile: it is now running.
        execution = get_execution(db, stored_id(session), stored_id(dd_type))

    previous = execution.status
    if not _switch(db, execution, ExecutionStatus.IN_PROGRESS, _STARTABLE):
        _refuse_start(db, execution)
    logger.info("Restarting execution %s (was %s)", execution.id, previous.value)
    return execution


def pause(db: Session, session: DDSession, dd_type: DDType) -> DDExecution:
    """Ask a running run to stop: the engine checks the status between questions."""
    execution = get_execution(db, stored_id(session), stored_id(dd_type))
    if not _switch(db, execution, ExecutionStatus.PAUSED, (ExecutionStatus.IN_PROGRESS,)):
        raise InvalidRequestError(f"Cannot pause execution with status {execution.status.value}")
    logger.info("Paused execution %s", execution.id)
    return execution


def resume(db: Session, session: DDSession, dd_type: DDType) -> DDExecution:
    """Mark the run in progress again, for the engine to go on with it.

    A run going on is not resumed a second time, unless it is stuck: then this
    takes it over.
    """
    execution = get_execution(db, stored_id(session), stored_id(dd_type))
    if not _switch(db, execution, ExecutionStatus.IN_PROGRESS, _RESUMABLE, or_stuck=True):
        if execution.status == ExecutionStatus.IN_PROGRESS:
            raise InvalidRequestError("DD processing already in progress")
        raise InvalidRequestError(f"Cannot resume execution with status {execution.status.value}")
    return execution


def run_in_background(
    run: Callable[..., Any], session_id: int, dd_type_id: int, *args: Any
) -> None:
    """Run the engine as a background task; on a crash, log it and mark the
    execution failed, so the run does not stay "in progress" forever."""
    try:
        run(*args)
    except Exception:
        logger.exception("Background run failed (session %s, DD type %s)", session_id, dd_type_id)
        db = database.SessionLocal()
        try:
            execution = find_execution(db, session_id, dd_type_id)
            if execution is not None:
                execution.status = ExecutionStatus.FAILED
                db.commit()
        except Exception:
            logger.exception("Could not mark the execution failed")
        finally:
            db.close()
