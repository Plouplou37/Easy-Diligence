"""
Vector Store Session Assignment
Handle assigning/unassigning vector stores to sessions
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.dd_types import DDType
from app.models.user import User
from app.models.vector_store import SessionVectorStore, VectorStore
from app.schemas.vector_stores import SessionVectorStoreAssignment

logger = logging.getLogger(__name__)
router = APIRouter()


def _scope_filter(query, dd_type_id):
    """Narrow to one assignment scope: a given DD type, or the session-wide row.

    NULL is a scope here, not a missing value, so it needs IS NULL rather than
    an equality that would never match.
    """
    if dd_type_id is not None:
        return query.filter(SessionVectorStore.dd_type_id == dd_type_id)
    return query.filter(SessionVectorStore.dd_type_id.is_(None))


@router.get("/session/{session_identifier}/assignments")
async def get_session_vector_store_assignments(
    session_identifier: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get all vector store assignments for a session"""
    # Verify session exists and user has access
    from app.models.session import DDSession

    try:
        session_id = int(session_identifier)
        session = db.query(DDSession).filter(DDSession.id == session_id).first()
    except ValueError:
        # Not an integer, treat as session_code
        session = db.query(DDSession).filter(DDSession.session_code == session_identifier).first()
        session_id = session.id if session else None

    if not session or session.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Get all assignments for this session with vector store details (all vector stores are shareable)
    # DDType is joined outer: dd_type_id is NULL on a session-wide assignment.
    assignments = (
        db.query(SessionVectorStore, VectorStore, DDType)
        .join(VectorStore, SessionVectorStore.vector_store_id == VectorStore.id)
        .outerjoin(DDType, SessionVectorStore.dd_type_id == DDType.id)
        .filter(SessionVectorStore.session_id == session_id)
        .all()
    )

    result = []
    for assignment, vector_store, dd_type in assignments:
        result.append(
            {
                "vector_store_id": vector_store.id,
                "vector_store_name": vector_store.name,
                "vector_store_description": vector_store.description,
                # Scope of the assignment. Both stay null for a session-wide one,
                # which the caller must read as "every DD type of the session".
                # They used to be omitted entirely, so the UI could not tell the
                # two scopes apart and showed neither.
                "dd_type_id": assignment.dd_type_id,
                "dd_type_code": dd_type.code if dd_type else None,
                "assigned_at": assignment.assigned_at,
                "session_id": session_id,
            }
        )

    return {"session_id": session_id, "session_name": session.name, "assignments": result}


@router.put("/{vector_store_id}/assign-session/{session_identifier}")
async def assign_vector_store_to_session(
    vector_store_id: str,
    session_identifier: str,
    payload: SessionVectorStoreAssignment | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Assign a vector store to a session, optionally to one DD type only.

    The body was never declared until now, so the dd_type_id the UI has always
    sent was dropped and every assignment landed session-wide -- which is why
    assigning a store to a single DD type appeared to work and never did.
    """
    # Verify vector store exists (shareable across users)
    vector_store = db.query(VectorStore).filter(VectorStore.id == vector_store_id).first()

    if not vector_store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vector store not found")

    # Verify session exists and user has access
    from app.models.session import DDSession

    try:
        session_id = int(session_identifier)
        session = db.query(DDSession).filter(DDSession.id == session_id).first()
    except ValueError:
        # Not an integer, treat as session_code
        session = db.query(DDSession).filter(DDSession.session_code == session_identifier).first()
        session_id = session.id if session else None

    if not session or session.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Scope of the assignment: a DD type, or the whole session when absent.
    dd_type_id = payload.dd_type_id if payload else None
    dd_type = None
    if dd_type_id is not None:
        dd_type = db.query(DDType).filter(DDType.id == dd_type_id).first()
        if not dd_type:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DD type not found")

    # Check if already assigned -- with the same scope. Without the DD type in
    # this filter, assigning a store to a second DD type was a silent no-op
    # that still answered 200.
    existing_assignment = _scope_filter(
        db.query(SessionVectorStore).filter(
            SessionVectorStore.vector_store_id == vector_store_id,
            SessionVectorStore.session_id == session_id,
        ),
        dd_type_id,
    ).first()

    if existing_assignment:
        return {
            "message": "Vector store already assigned to session",
            "assignment": {
                "vector_store_id": vector_store_id,
                "session_id": session_id,
                "dd_type_id": dd_type_id,
                "dd_type_code": dd_type.code if dd_type else None,
                "assigned_at": existing_assignment.assigned_at,
            },
        }

    # Create assignment
    try:
        assignment = SessionVectorStore(
            vector_store_id=vector_store_id,
            session_id=session_id,
            dd_type_id=dd_type_id,
            assigned_by=current_user.id,
            assigned_at=func.now(),
        )

        db.add(assignment)
        db.commit()

        return {
            "message": "Vector store assigned to session successfully",
            "assignment": {
                "vector_store_id": vector_store_id,
                "vector_store_name": vector_store.name,
                "session_id": session_id,
                "session_name": session.name,
                "dd_type_id": dd_type_id,
                "dd_type_code": dd_type.code if dd_type else None,
                "assigned_at": assignment.assigned_at,
            },
        }

    except Exception:
        db.rollback()
        logger.exception("Failed to assign vector store")
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign vector store",
        )


@router.delete("/{vector_store_id}/assign-session/{session_identifier}")
async def unassign_vector_store_from_session(
    vector_store_id: str,
    session_identifier: str,
    dd_type_code: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Unassign a vector store, from one DD type or from the whole session.

    dd_type_code has always been sent by the UI and never read here, so the
    first matching row was deleted whatever its scope -- removing the store
    from one card could remove it from another.
    """
    # Verify vector store exists (shareable across users)
    vector_store = db.query(VectorStore).filter(VectorStore.id == vector_store_id).first()

    if not vector_store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vector store not found")

    # Verify session exists and user has access
    from app.models.session import DDSession

    try:
        session_id = int(session_identifier)
        session = db.query(DDSession).filter(DDSession.id == session_id).first()
    except ValueError:
        # Not an integer, treat as session_code
        session = db.query(DDSession).filter(DDSession.session_code == session_identifier).first()
        session_id = session.id if session else None

    if not session or session.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Find and remove assignment -- the one with the scope that was asked for.
    query = db.query(SessionVectorStore).filter(
        SessionVectorStore.vector_store_id == vector_store_id,
        SessionVectorStore.session_id == session_id,
    )
    dd_type = None
    if dd_type_code:
        dd_type = db.query(DDType).filter(DDType.code == dd_type_code).first()
        if not dd_type:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DD type not found")

    assignment = _scope_filter(query, dd_type.id if dd_type else None).first()

    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    try:
        db.delete(assignment)
        db.commit()

        return {
            "message": "Vector store unassigned from session successfully",
            "vector_store_id": vector_store_id,
            "session_id": session_id,
        }

    except Exception:
        db.rollback()
        logger.exception("Failed to unassign vector store")
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unassign vector store",
        )
