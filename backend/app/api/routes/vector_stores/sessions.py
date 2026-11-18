"""Assigning vector stores to sessions: to the whole session, or to one DD type.

Anyone who may access the session may change its assignments, and any store
may serve it: a colleague's store can be assigned.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_accessible_session, get_current_active_user
from app.core.database import get_db
from app.models.session import DDSession
from app.models.user import User
from app.schemas.vector_stores import SessionVectorStoreAssignment
from app.services import vector_stores

router = APIRouter()


@router.get("/session/{session_identifier}/assignments")
def get_session_vector_store_assignments(
    session: DDSession = Depends(get_accessible_session),
    db: Session = Depends(get_db),
):
    """The stores assigned to a session, each with its scope."""
    return {
        "session_id": session.id,
        "session_name": session.name,
        "assignments": vector_stores.list_assignments(db, session),
    }


@router.put("/{vector_store_id}/assign-session/{session_identifier}")
def assign_vector_store_to_session(
    vector_store_id: str,
    payload: SessionVectorStoreAssignment | None = None,
    session: DDSession = Depends(get_accessible_session),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Assign a store to a session, or to one of its DD types (`dd_type_id`)."""
    dd_type_id = payload.dd_type_id if payload else None
    return vector_stores.assign(db, vector_store_id, session, dd_type_id, current_user)


@router.delete("/{vector_store_id}/assign-session/{session_identifier}")
def unassign_vector_store_from_session(
    vector_store_id: str,
    dd_type_code: str | None = None,
    session: DDSession = Depends(get_accessible_session),
    db: Session = Depends(get_db),
):
    """Remove an assignment: from one DD type (`dd_type_code`), or session-wide."""
    vector_stores.unassign(db, vector_store_id, session, dd_type_code)
    return {
        "message": "Vector store unassigned from session successfully",
        "vector_store_id": vector_store_id,
        "session_id": session.id,
    }
