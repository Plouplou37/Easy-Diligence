"""
Utility functions for common operations
"""

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlmodel import col

from app.models.session import DDSession


def build_company_info(company) -> dict:
    """Context describing the DD subject, as handed to the model.

    Carries the fund AND its management company as two distinct entities: the
    questionnaires ask about both, and without the distinction the model -- and
    the web search behind it -- has to guess which one a question targets.

    Single source of truth for the three call sites (start, resume, regenerate)
    so a new field reaches all of them at once. Returns {} when there is no
    company, which _build_system_prompt handles.
    """
    if company is None:
        return {}
    return {
        "name": company.name,
        "website_url": getattr(company, "website_url", None),
        "description": getattr(company, "description", None),
        "management_company_name": getattr(company, "management_company_name", None),
        "management_company_website": getattr(company, "management_company_website", None),
    }


def get_session_by_identifier(db: Session, session_identifier: str) -> tuple[DDSession, int]:
    """
    Get session by ID or session code.

    Args:
        db: Database session
        session_identifier: Either integer ID or session code string

    Returns:
        tuple: (session_object, session_id)

    Raises:
        HTTPException: If session not found
    """
    try:
        session = db.get(DDSession, int(session_identifier))
    except ValueError:
        # Not an integer: a session code.
        session = (
            db.query(DDSession).filter(col(DDSession.session_code) == session_identifier).first()
        )

    if session is None or session.id is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return session, session.id
