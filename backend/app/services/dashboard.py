"""Dashboard: every session of the user, with the state of each of its DD types.

One request, a handful of grouped queries whatever the number of sessions. The
Dashboard used to call ``/session/{id}/status`` once per session every 5 s, and
that endpoint runs about five queries per DD type and loads every answer row
just to add up counters.

Read-only. In particular the summary batches are read from
``dd_summary_batches`` as stored: the batch GET of ``summaries.py`` calls
OpenAI and writes to the database, which a dashboard must never fan out.
"""

import json
from collections.abc import Iterable, Mapping
from datetime import datetime
from typing import Any

from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session, joinedload
from sqlmodel import col

from app.engine.summarizer import PENDING_BATCH_STATUSES
from app.models.answer import DDAnswer
from app.models.base import relation
from app.models.dd_types import DDType
from app.models.execution import DDExecution
from app.models.questions import DDQuestion, DDSection
from app.models.session import DDSession
from app.models.summary import DDSummary, DDSummaryBatch
from app.models.user import User
from app.services.authz import filter_sessions_for_user

# "To review" = every current answer not approved yet, failures aside. A freshly
# generated answer is stored as `completed`, not `needs_review`: counting only
# the latter left every AI answer out.
TO_REVIEW_STATUSES = {"completed", "needs_review", "draft", "rejected"}


def _status_value(status) -> str:
    """Enum member or plain string -> lower-case value."""
    return str(getattr(status, "value", status) or "").lower()


def _execution_status(status) -> str:
    # Same mapping as /session/{id}/status: the frontend knows `completed`.
    value = _status_value(status) or "not_started"
    return "completed" if value == "generated" else value


def _latest(*values) -> datetime | None:
    present = [v for v in values if v is not None]
    return max(present) if present else None


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _selected_codes(dd_types_json: str | None) -> list[str]:
    """Codes stored on the session at creation (`[{"code", "name"}]`)."""
    try:
        return [t["code"] for t in json.loads(dd_types_json or "[]") if t.get("code")]
    except (ValueError, TypeError, AttributeError, KeyError):
        return []


def build_dashboard_rows(
    sessions: Iterable,
    executions: Iterable,
    answer_counts: Iterable,
    answered_counts: Iterable,
    summaries: Iterable,
    batches: Iterable,
    question_totals: dict[int, int],
    dd_types_by_code: Mapping[str, Any],
) -> dict:
    """Assemble the dashboard payload from the rows of the grouped queries.

    Pure function (no database access), so it can be tested with plain objects.

    - executions: (session_id, dd_type_id, code, name, is_active, status, updated_at)
    - answer_counts: (session_id, dd_type_id, status, count, last_created, last_edited)
    - answered_counts: (session_id, dd_type_id, distinct answered questions)
    - summaries: (session_id, dd_type_id, has_synthesis, synthesis_updated_at, last_updated)
    - batches: (session_id, dd_type_id, status, updated_at)
    """
    per_dd: dict[tuple, dict] = {}

    def entry(session_id, dd_type_id):
        key = (session_id, dd_type_id)
        if key not in per_dd:
            per_dd[key] = {
                "dd_type_id": dd_type_id,
                "status": "not_started",
                "answered": 0,
                "to_review": 0,
                "approved": 0,
                "failed": 0,
                "has_synthesis": False,
                "synthesis_updated_at": None,
                "batch_status": None,
                "last_answer_at": None,
                "_activity": None,
            }
        return per_dd[key]

    for session_id, dd_type_id, code, name, is_active, status, updated_at in executions:
        e = entry(session_id, dd_type_id)
        e.update(code=code, name=name, is_active=is_active, status=_execution_status(status))
        e["_activity"] = _latest(e["_activity"], updated_at)

    for session_id, dd_type_id, status, count, last_created, last_edited in answer_counts:
        e = entry(session_id, dd_type_id)
        value = _status_value(status)
        if value == "approved":
            e["approved"] += count
        elif value == "failed":
            e["failed"] += count
        elif value in TO_REVIEW_STATUSES:
            e["to_review"] += count
        e["last_answer_at"] = _latest(e["last_answer_at"], last_created)
        e["_activity"] = _latest(e["_activity"], last_created, last_edited)

    for session_id, dd_type_id, answered in answered_counts:
        entry(session_id, dd_type_id)["answered"] = answered or 0

    for session_id, dd_type_id, has_synthesis, synthesis_updated_at, last_updated in summaries:
        e = entry(session_id, dd_type_id)
        e["has_synthesis"] = bool(has_synthesis)
        e["synthesis_updated_at"] = synthesis_updated_at
        e["_activity"] = _latest(e["_activity"], last_updated)

    for session_id, dd_type_id, status, updated_at in batches:
        e = entry(session_id, dd_type_id)
        e["batch_status"] = status
        e["_activity"] = _latest(e["_activity"], updated_at)

    totals = {"sessions": 0, "to_review": 0, "running": 0, "syntheses_ready": 0}
    rows = []
    for session in sessions:
        totals["sessions"] += 1
        runs = {dd_id: e for (s_id, dd_id), e in per_dd.items() if s_id == session.id}

        # DD types chosen at creation but never started have no execution row:
        # they still belong on the dashboard, as "not started".
        for code in _selected_codes(session.dd_types_json):
            dd_type = dd_types_by_code.get(code)
            if dd_type is not None and dd_type.id not in runs:
                runs[dd_type.id] = entry(session.id, dd_type.id)
                runs[dd_type.id].update(
                    code=dd_type.code, name=dd_type.name, is_active=dd_type.is_active
                )

        dd_rows = []
        last_activity = session.created_at
        for e in runs.values():
            if "code" not in e:
                continue  # answers or summaries of a DD type with no execution nor selection
            e["total_questions"] = question_totals.get(e["dd_type_id"], 0)
            e["percentage"] = (
                min(round(100 * e["answered"] / e["total_questions"]), 100)
                if e["total_questions"]
                else 0
            )
            last_activity = _latest(last_activity, e.pop("_activity"))
            for field in ("synthesis_updated_at", "last_answer_at"):
                e[field] = _iso(e[field])
            dd_rows.append(e)

            totals["to_review"] += e["to_review"]
            totals["running"] += 1 if e["status"] == "in_progress" else 0
            totals["syntheses_ready"] += 1 if e["has_synthesis"] else 0

        dd_rows.sort(key=lambda e: e["name"] or "")
        company = getattr(session, "company", None)
        creator = getattr(session, "creator", None)
        rows.append(
            {
                "id": session.id,
                "session_code": session.session_code,
                "name": session.name,
                "description": session.description,
                "company_name": getattr(company, "name", None),
                "management_company_name": getattr(company, "management_company_name", None),
                "created_by": session.created_by,
                "assigned_to": session.assigned_to,
                "created_by_username": getattr(creator, "username", None),
                "created_at": _iso(session.created_at),
                "last_activity_at": _iso(last_activity),
                "batch_pending": any(e["batch_status"] in PENDING_BATCH_STATUSES for e in dd_rows),
                "dd_types": dd_rows,
            }
        )

    rows.sort(key=lambda r: r["last_activity_at"] or "", reverse=True)
    return {"sessions": rows, "totals": totals}


def dashboard(db: Session, user: User) -> dict[str, Any]:
    """Sessions visible to the user, each with the state of its DD types."""
    sessions = (
        filter_sessions_for_user(db.query(DDSession), user)
        .options(joinedload(relation(DDSession.company)), joinedload(relation(DDSession.creator)))
        .all()
    )
    if not sessions:
        return {
            "sessions": [],
            "totals": {"sessions": 0, "to_review": 0, "running": 0, "syntheses_ready": 0},
        }
    ids = [s.id for s in sessions]

    executions = (
        db.query(
            col(DDExecution.session_id),
            col(DDExecution.dd_type_id),
            col(DDType.code),
            col(DDType.name),
            col(DDType.is_active),
            col(DDExecution.status),
            col(DDExecution.updated_at),
        )
        .join(DDType, col(DDType.id) == col(DDExecution.dd_type_id))
        .filter(col(DDExecution.session_id).in_(ids))
        .all()
    )

    # Grouped on the execution's DD type: dd_answers.dd_type_id is nullable.
    current_answers = and_(
        col(DDAnswer.execution_id) == col(DDExecution.id), col(DDAnswer.is_current).is_(True)
    )
    answer_counts = (
        db.query(
            col(DDExecution.session_id),
            col(DDExecution.dd_type_id),
            col(DDAnswer.status),
            func.count(col(DDAnswer.id)),
            func.max(col(DDAnswer.created_at)),
            func.max(col(DDAnswer.edited_at)),
        )
        .join(DDAnswer, current_answers)
        .filter(col(DDExecution.session_id).in_(ids))
        .group_by(col(DDExecution.session_id), col(DDExecution.dd_type_id), col(DDAnswer.status))
        .all()
    )
    # Same progress rule as /session/{id}/status: distinct questions with a text.
    answered_counts = (
        db.query(
            col(DDExecution.session_id),
            col(DDExecution.dd_type_id),
            func.count(func.distinct(col(DDAnswer.question_id))),
        )
        .join(DDAnswer, current_answers)
        .filter(col(DDExecution.session_id).in_(ids), col(DDAnswer.answer_text).isnot(None))
        .group_by(col(DDExecution.session_id), col(DDExecution.dd_type_id))
        .all()
    )

    is_synthesis = col(DDSummary.section_id).is_(None)
    summaries = (
        db.query(
            col(DDSummary.session_id),
            col(DDSummary.dd_type_id),
            func.max(case((is_synthesis, 1), else_=0)),
            func.max(case((is_synthesis, col(DDSummary.updated_at)), else_=None)),
            func.max(col(DDSummary.updated_at)),
        )
        .filter(col(DDSummary.session_id).in_(ids))
        .group_by(col(DDSummary.session_id), col(DDSummary.dd_type_id))
        .all()
    )

    batches = (
        db.query(
            col(DDSummaryBatch.session_id),
            col(DDSummaryBatch.dd_type_id),
            col(DDSummaryBatch.status),
            col(DDSummaryBatch.updated_at),
        )
        .filter(col(DDSummaryBatch.session_id).in_(ids))
        .all()
    )

    selected = {code for s in sessions for code in _selected_codes(s.dd_types_json)}
    dd_types_by_code = (
        {t.code: t for t in db.query(DDType).filter(col(DDType.code).in_(selected)).all()}
        if selected
        else {}
    )
    dd_type_ids = {row[1] for row in executions} | {t.id for t in dd_types_by_code.values()}
    question_totals: dict[int, int] = (
        {
            row[0]: row[1]
            for row in db.query(col(DDSection.dd_type_id), func.count(col(DDQuestion.id)))
            .join(DDQuestion, col(DDQuestion.section_id) == col(DDSection.id))
            .filter(col(DDSection.dd_type_id).in_(dd_type_ids))
            .group_by(col(DDSection.dd_type_id))
            .all()
        }
        if dd_type_ids
        else {}
    )

    return build_dashboard_rows(
        sessions,
        executions,
        answer_counts,
        answered_counts,
        summaries,
        batches,
        question_totals,
        dd_types_by_code,
    )
