"""DD sessions: creation, reading, progress of the runs, listing, deletion."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_accessible_session, get_current_active_user
from app.core.database import get_db
from app.core.pagination import PaginationMeta, PaginationParams
from app.models.base import stored_id
from app.models.session import (
    DDSession,
    SessionCreate,
    SessionListResponse,
    SessionResponse,
    SessionStatusResponse,
)
from app.models.user import User
from app.services import sessions as sessions_service

router = APIRouter()


@router.post("/", response_model=SessionResponse)
def create_session(
    data: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a DD session on a company the user can see."""
    return SessionResponse.of(sessions_service.create_session(db, data, current_user))


@router.get("/{session_identifier}", response_model=SessionResponse)
def get_session(session: DDSession = Depends(get_accessible_session)):
    """A session, by id or session code."""
    return SessionResponse.of(session)


@router.get("/{session_identifier}/status", response_model=SessionStatusResponse)
def get_session_status(
    session: DDSession = Depends(get_accessible_session),
    db: Session = Depends(get_db),
):
    """The session with the progress of each of its DD type runs."""
    return SessionStatusResponse(
        id=stored_id(session),
        progress=sessions_service.session_progress(db, session),
    )


@router.get("/", response_model=SessionListResponse)
def list_sessions(
    company_id: int | None = None,
    page: int = 1,
    limit: int = 50,
    created_by: int | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """The user's sessions (an admin's: all), filtered and paginated."""
    params = PaginationParams(page=page, limit=limit)
    sessions, total, filters = sessions_service.list_sessions(
        db,
        current_user,
        params,
        company_id=company_id,
        created_by=created_by,
        search=search,
    )

    return SessionListResponse.of(
        [SessionResponse.of(session) for session in sessions],
        PaginationMeta.from_params(params, total),
        filters,
    )


@router.delete("/{session_identifier}")
def delete_session(
    session: DDSession = Depends(get_accessible_session),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a session, its runs and answers. Only its creator may."""
    session_id, session_code = session.id, session.session_code
    sessions_service.delete_session(db, session, current_user)
    return {
        "message": "Session deleted successfully",
        "session_id": session_id,
        "session_code": session_code,
    }
