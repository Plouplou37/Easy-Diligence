"""Stored summaries: listing and hand edits. Generating them is the engine's
(engine/summarizer.py)."""

from sqlalchemy.orm import Session
from sqlmodel import col

from app.core.exceptions import NotFoundError
from app.models.session import DDSession
from app.models.summary import DDSummary, DDSummaryResponse
from app.models.user import User
from app.services.authz import assert_session_access
from app.services.dd_types import get_dd_type_by_code


def to_response(summary: DDSummary) -> DDSummaryResponse:
    """A summary, with the labels the page shows."""
    return DDSummaryResponse(
        id=summary.id or 0,
        session_id=summary.session_id,
        dd_type_id=summary.dd_type_id,
        section_id=summary.section_id,
        summary_text=summary.summary_text,
        edited_by=summary.edited_by,
        generated_at=summary.generated_at,
        updated_at=summary.updated_at,
        dd_type_code=summary.dd_type.code if summary.dd_type else None,
        dd_type_name=summary.dd_type.name if summary.dd_type else None,
        section_title=summary.section.title if summary.section else None,
    )


def list_summaries(
    db: Session, session: DDSession, user: User, dd_type: str | None = None
) -> list[DDSummary]:
    """The summaries of a session, of one DD type if given."""
    query = db.query(DDSummary).filter(col(DDSummary.session_id) == session.id)
    if dd_type:
        query = query.filter(col(DDSummary.dd_type_id) == get_dd_type_by_code(db, dd_type, user).id)
    return query.order_by(col(DDSummary.id)).all()


def edit_summary(db: Session, summary_id: int, text: str, user: User) -> DDSummary:
    """A reviewer's edit of a summary, before the export."""
    summary = db.get(DDSummary, summary_id)
    if summary is None:
        raise NotFoundError("Summary not found")
    session = db.get(DDSession, summary.session_id)
    if session is None:
        raise NotFoundError("Session not found")
    assert_session_access(session, user)
    summary.summary_text = text
    summary.edited_by = user.id
    db.commit()
    db.refresh(summary)
    return summary
