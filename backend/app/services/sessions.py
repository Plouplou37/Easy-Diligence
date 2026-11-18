"""DD sessions: lookup, creation, listing, deletion, and the progress of their runs."""

import json
import secrets
import string
from datetime import datetime
from typing import Any

from sqlalchemy import case, distinct, func, or_
from sqlalchemy.orm import Session, joinedload
from sqlmodel import col

from app.core.exceptions import InvalidRequestError, NotFoundError, PermissionDeniedError
from app.core.pagination import PaginationParams, paginate_query
from app.models.answer import AnswerStatus, DDAnswer
from app.models.base import relation, stored_id
from app.models.company import Company
from app.models.dd_types import DDType
from app.models.execution import DDExecution, ExecutionStatus
from app.models.questions import DDQuestion, DDSection
from app.models.session import DDSession, SessionCreate, SessionStatus
from app.models.user import User
from app.services.authz import (
    assert_company_view,
    assert_session_access,
    filter_dd_types_for_user,
    filter_sessions_for_user,
)

# A session can be deleted unless it is running or finished.
_UNDELETABLE = (SessionStatus.IN_PROGRESS, SessionStatus.COMPLETED)


# --- Lookup -----------------------------------------------------------------


def get_session(db: Session, identifier: str) -> DDSession:
    """The session with this id, or with this session code."""
    try:
        session = db.get(DDSession, int(identifier))
    except ValueError:
        session = db.query(DDSession).filter(col(DDSession.session_code) == identifier).first()
    if session is None:
        raise NotFoundError("Session not found")
    return session


def get_session_for_user(db: Session, identifier: str, user: User) -> DDSession:
    """The session, if the user may access it (404 if unknown, 403 if not theirs)."""
    session = get_session(db, identifier)
    assert_session_access(session, user)
    return session


# --- Creation, listing, deletion ---------------------------------------------


def _new_session_code(name: str, user_id: int) -> str:
    """NAME-USER-RANDOM: 3 letters of the name, the user id's last two digits,
    4 random characters."""
    name_part = "".join(name.split())[:3].upper() or "SES"
    user_part = str(user_id)[-2:].zfill(2)
    alphabet = string.ascii_uppercase + string.digits
    random_part = "".join(secrets.choice(alphabet) for _ in range(4))
    return f"{name_part}-{user_part}-{random_part}"


def create_session(db: Session, data: SessionCreate, user: User) -> DDSession:
    """A new session on a company the user can see, with the DD types to run:
    the ones selected, or else every active type the user can see."""
    company = db.get(Company, data.company_id)
    if company is None:
        raise NotFoundError("Company not found")
    assert_company_view(company, user)

    code = _new_session_code(data.name, stored_id(user))
    while db.query(DDSession).filter(col(DDSession.session_code) == code).first():
        code = _new_session_code(data.name, stored_id(user))

    dd_types = filter_dd_types_for_user(
        db.query(DDType).filter(col(DDType.is_active).is_(True)), user
    )
    if data.dd_type_ids:
        dd_types = dd_types.filter(col(DDType.id).in_(data.dd_type_ids))
    selected = dd_types.order_by(col(DDType.order_index), col(DDType.id)).all()

    session = DDSession(
        session_code=code,
        company_id=data.company_id,
        name=data.name,
        description=data.description,
        status=SessionStatus.CREATED,
        created_by=user.id,
        assigned_to=user.id,
        # The DD types chosen for the session, read by the frontend.
        dd_types_json=(
            json.dumps([{"code": t.code, "name": t.name} for t in selected]) if selected else None
        ),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def list_sessions(
    db: Session,
    user: User,
    params: PaginationParams,
    *,
    company_id: int | None = None,
    status: str | None = None,
    created_by: int | None = None,
    search: str | None = None,
) -> tuple[list[DDSession], int, dict[str, Any]]:
    """The user's sessions (an admin's: all), filtered, most recent first.

    Returns the page, the total count, and the filters that were applied.
    """
    query = filter_sessions_for_user(db.query(DDSession), user)
    filters: dict[str, Any] = {}

    if company_id:
        query = query.filter(col(DDSession.company_id) == company_id)
        filters["company_id"] = company_id
    if status:
        try:
            query = query.filter(col(DDSession.status) == SessionStatus(status))
        except ValueError:
            raise InvalidRequestError(f"Unknown session status '{status}'") from None
        filters["status"] = status
    if created_by:
        query = query.filter(col(DDSession.created_by) == created_by)
        filters["created_by"] = created_by
    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(col(DDSession.name).ilike(term), col(DDSession.description).ilike(term))
        )
        filters["search"] = search

    query = query.options(
        joinedload(relation(DDSession.company)),
        joinedload(relation(DDSession.creator)),
    ).order_by(col(DDSession.created_at).desc())

    total = query.count()
    return paginate_query(query, params).all(), total, filters


def delete_session(db: Session, session: DDSession, user: User) -> None:
    """Delete a session and everything hanging off it (cascade).

    Only its creator may, admins included, and not while it runs or once done.
    """
    if session.created_by != user.id:
        raise PermissionDeniedError("Only the session creator can delete this session")
    if session.status in _UNDELETABLE:
        status = session.status.value if session.status else "unknown"
        raise InvalidRequestError(
            f"Cannot delete session with status '{status}'. Only sessions with status "
            "'created', 'documents_uploaded', 'failed', or 'paused' can be deleted."
        )
    db.delete(session)
    db.commit()


# --- Progress of the runs ------------------------------------------------------


def _cites_documents(sources: Any) -> bool:
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


# Execution status -> what the progress card shows. "generated" is finished,
# from the user's point of view.
_UI_STATUS = {ExecutionStatus.GENERATED.value: "completed"}


def _count_by_section(query: Any) -> dict[int, int]:
    """{section id: count} from a query of (section id, count) rows."""
    return {row[0]: row[1] for row in query.all()}


def _sections_progress(db: Session, execution: DDExecution) -> list[dict[str, Any]]:
    """Answered / total questions of each section of the execution's DD type."""
    sections = (
        db.query(DDSection)
        .filter(col(DDSection.dd_type_id) == execution.dd_type_id)
        .order_by(col(DDSection.order_index))
        .all()
    )
    if not sections:
        return []
    section_ids = [s.id for s in sections]

    totals = _count_by_section(
        db.query(col(DDQuestion.section_id), func.count(col(DDQuestion.id)))
        .filter(col(DDQuestion.section_id).in_(section_ids))
        .group_by(col(DDQuestion.section_id))
    )
    answered = _count_by_section(
        db.query(col(DDQuestion.section_id), func.count(distinct(col(DDAnswer.question_id))))
        .join(DDAnswer, col(DDAnswer.question_id) == col(DDQuestion.id))
        .filter(
            col(DDAnswer.execution_id) == execution.id,
            col(DDQuestion.section_id).in_(section_ids),
            col(DDAnswer.answer_text).isnot(None),
        )
        .group_by(col(DDQuestion.section_id))
    )

    progress = []
    for section in sections:
        total = totals.get(stored_id(section), 0)
        done = answered.get(stored_id(section), 0)
        if done == 0:
            status = "not_started"
        elif done == total:
            status = "completed"
        else:
            status = "in_progress"
        progress.append(
            {
                "name": section.title,
                "status": status,
                "questions_completed": done,
                "total_questions": total,
                "percentage": done / total * 100 if total else 0,
            }
        )
    return progress


def _last_error(db: Session, execution: DDExecution) -> str | None:
    """The first error of a failed run (a paused run has none)."""
    if execution.status != ExecutionStatus.FAILED:
        return None
    first_failed = (
        db.query(DDAnswer)
        .filter(
            col(DDAnswer.execution_id) == execution.id,
            col(DDAnswer.status) == AnswerStatus.FAILED,
        )
        .order_by(col(DDAnswer.created_at).asc())
        .first()
    )
    if first_failed is None or not first_failed.error_message:
        return None
    error_type = first_failed.error_type.value if first_failed.error_type else "unknown"
    return f"{error_type}: {first_failed.error_message}"


def session_progress(db: Session, session: DDSession) -> list[dict[str, Any]]:
    """The progress of each DD type run of the session, as the session page shows it."""
    executions = (
        db.query(DDExecution)
        .options(joinedload(relation(DDExecution.dd_type)))
        .filter(col(DDExecution.session_id) == session.id)
        .all()
    )
    if not executions:
        return []

    # Questions answered (with a text) and completed, per execution, in one query.
    answered_by_execution = {
        row.execution_id: row.answered
        for row in db.query(
            col(DDAnswer.execution_id),
            func.count(
                distinct(
                    case(
                        (col(DDAnswer.answer_text).isnot(None), col(DDAnswer.question_id)),
                        else_=None,
                    )
                )
            ).label("answered"),
        )
        .filter(col(DDAnswer.execution_id).in_([e.id for e in executions]))
        .group_by(col(DDAnswer.execution_id))
        .all()
    }

    progress = []
    for execution in executions:
        status = execution.status or ExecutionStatus.NOT_STARTED.value
        answered = answered_by_execution.get(execution.id, 0)
        processed = 0 if status == ExecutionStatus.NOT_STARTED else answered
        total = (
            db.query(DDQuestion)
            .join(DDSection, col(DDQuestion.section_id) == col(DDSection.id))
            .filter(col(DDSection.dd_type_id) == execution.dd_type_id)
            .count()
        )

        # Only the current version of each answer: superseded versions and
        # failed retries stay in the table, and counting their tokens inflated
        # the total well past what the run actually cost.
        answers = (
            db.query(DDAnswer)
            .filter(
                col(DDAnswer.execution_id) == execution.id,
                col(DDAnswer.is_current).is_(True),
            )
            .all()
        )
        times = [a.created_at for a in answers if a.created_at]

        # Time actually spent answering, measured on the answers themselves:
        # the execution row is only written at the start and at the end of a
        # run, and a resumed run would count its idle hours.
        elapsed = 0
        if times:
            first = min(times)
            if status == ExecutionStatus.IN_PROGRESS:
                elapsed = int((datetime.now(first.tzinfo) - first).total_seconds())
            else:
                elapsed = int((max(times) - first).total_seconds())

        progress.append(
            {
                "dd_type": execution.dd_type.code if execution.dd_type else None,
                "dd_type_name": execution.dd_type.name if execution.dd_type else None,
                "status": _UI_STATUS.get(status, status),
                "questions_completed": processed,
                "total_questions": total,
                "percentage": processed / total * 100 if total else 0,
                "sections_progress": _sections_progress(db, execution),
                "tokens_used": sum(a.tokens_used or 0 for a in answers),
                # How many answers rest on the assigned documents.
                "answers_with_documents": sum(1 for a in answers if _cites_documents(a.sources)),
                "answers_counted": len(answers),
                "time_elapsed": elapsed,
                "current_section": None,  # not tracked
                "current_question": None,  # not tracked
                "last_error": _last_error(db, execution),
            }
        )
    return progress
