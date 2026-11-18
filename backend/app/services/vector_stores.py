"""Vector stores: the stores (kept at OpenAI, listed in our database), their
files, and their assignment to sessions.

Reading never deletes. A store that has expired or disappeared at OpenAI is
listed with the status "expired" or "missing"; `purge_stale` (the page's
Refresh button) removes those from the database.

The OpenAI calls block: the routes call these functions from worker threads.
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from openai import NotFoundError as OpenAINotFound
from sqlalchemy.orm import Session
from sqlmodel import col

from app.core.cache import CacheInvalidator, cached
from app.core.exceptions import NotFoundError
from app.engine.openai_client import OpenAIProcessor
from app.models.base import stored_id
from app.models.dd_types import DDType
from app.models.session import DDSession
from app.models.user import User
from app.models.vector_store import (
    SessionVectorStore,
    VectorStore,
    VectorStoreCreate,
    VectorStoreResponse,
    VectorStoreUpdate,
)
from app.services.authz import user_is_admin
from app.services.dd_types import get_dd_type_by_code

logger = logging.getLogger(__name__)

CACHE_TTL = 300  # seconds

# Statuses of a store that is gone at OpenAI.
STALE = ("expired", "missing")


def openai_client() -> OpenAIProcessor:
    return OpenAIProcessor()


def _gone(error: Exception) -> bool:
    """Whether OpenAI answered that the store (or file) does not exist."""
    return isinstance(error, OpenAINotFound) or "404" in str(error)


# --- Stores -------------------------------------------------------------------


def get_owned_store(db: Session, store_id: str, user: User) -> VectorStore:
    """The store, if it is the user's (or the user is an admin). 404 otherwise,
    so that others' store ids cannot be probed."""
    store = db.get(VectorStore, store_id)
    if store is None or (not user_is_admin(user) and store.created_by != user.id):
        raise NotFoundError("Vector store not found")
    return store


def _response(store: VectorStore, info: dict[str, Any] | None, status: str) -> VectorStoreResponse:
    info = info or {}
    return VectorStoreResponse(
        id=store.id,
        name=store.name,
        description=store.description,
        created_at=store.created_at,
        updated_at=store.updated_at,
        file_count=info.get("file_counts", {}).get("total", 0),
        status=status,
        total_bytes=info.get("usage_bytes", 0),
        expires_at=info.get("expires_at"),
        expires_after_days=info.get("expires_after_days"),
        last_active_at=info.get("last_active_at"),
    )


def _describe(client: OpenAIProcessor, store: VectorStore) -> VectorStoreResponse:
    """The store with what OpenAI says of it now."""
    try:
        info = client.get_vector_store_info(store.id)
    except Exception as error:
        if _gone(error):
            return _response(store, None, "missing")
        logger.warning("OpenAI could not describe vector store %s: %s", store.id, error)
        return _response(store, None, "error")
    return _response(store, info, info.get("status", "unknown"))


def _visible_stores(db: Session, user: User) -> list[VectorStore]:
    query = db.query(VectorStore)
    if not user_is_admin(user):
        query = query.filter(col(VectorStore.created_by) == user.id)
    return query.order_by(col(VectorStore.created_at).desc()).all()


def _describe_all(stores: list[VectorStore]) -> list[VectorStoreResponse]:
    if not stores:
        return []
    client = openai_client()
    with ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(lambda store: _describe(client, store), stores))


def list_stores(db: Session, user: User) -> list[dict[str, Any]]:
    """The user's stores (an admin's: all), newest first, with their state at
    OpenAI. Cached: listing asks OpenAI about every store."""

    def compute() -> list[dict[str, Any]]:
        return [r.model_dump() for r in _describe_all(_visible_stores(db, user))]

    return cached(f"vector_stores:{user.id}", CACHE_TTL, compute)


def purge_stale(db: Session, user: User) -> int:
    """Remove from the database the user's stores that have expired or
    disappeared at OpenAI, with their assignments. Returns how many."""
    stores = _visible_stores(db, user)
    stale = [r.id for r in _describe_all(stores) if r.status in STALE]
    if stale:
        db.query(SessionVectorStore).filter(
            col(SessionVectorStore.vector_store_id).in_(stale)
        ).delete(synchronize_session=False)
        db.query(VectorStore).filter(col(VectorStore.id).in_(stale)).delete(
            synchronize_session=False
        )
        db.commit()
        logger.info("Removed %d stale vector store(s)", len(stale))
    CacheInvalidator.invalidate_vector_store_cache()
    return len(stale)


def get_store(db: Session, store: VectorStore) -> VectorStoreResponse:
    return _describe(openai_client(), store)


def create_store(db: Session, data: VectorStoreCreate, user: User) -> VectorStoreResponse:
    """A new store at OpenAI, recorded as the user's."""
    store_id = openai_client().create_vector_store(
        name=data.name, expires_after_days=data.expires_after_days
    )
    store = VectorStore(
        id=store_id, name=data.name, description=data.description, created_by=stored_id(user)
    )
    db.add(store)
    db.commit()
    db.refresh(store)
    CacheInvalidator.invalidate_vector_store_cache()
    return _response(store, None, "completed")


def update_store(db: Session, store: VectorStore, data: VectorStoreUpdate) -> VectorStoreResponse:
    """Rename the store (at OpenAI too) or change its description."""
    client = openai_client()
    if data.name and data.name != store.name:
        client.update_vector_store_name(store.id, data.name)
        store.name = data.name
    if data.description is not None:
        store.description = data.description
    db.commit()
    db.refresh(store)
    CacheInvalidator.invalidate_vector_store_cache()
    return _describe(client, store)


def delete_store(db: Session, store: VectorStore) -> None:
    """Delete the store at OpenAI (already gone is fine), then here, with its
    assignments."""
    try:
        openai_client().delete_vector_store(store.id)
    except Exception as error:
        if not _gone(error):
            raise
    db.query(SessionVectorStore).filter(col(SessionVectorStore.vector_store_id) == store.id).delete(
        synchronize_session=False
    )
    db.delete(store)
    db.commit()
    CacheInvalidator.invalidate_vector_store_cache()


# --- Files --------------------------------------------------------------------


def list_files(store: VectorStore) -> list[dict[str, Any]]:
    """The files of the store, from OpenAI. Cached."""

    def compute() -> list[dict[str, Any]]:
        try:
            return openai_client().list_vector_store_files(store.id)
        except Exception as error:
            if _gone(error):
                raise NotFoundError("Vector store no longer exists") from error
            raise

    return cached(f"vector_store_files:{store.id}", CACHE_TTL, compute)


def add_file(store: VectorStore, content: bytes, filename: str) -> dict[str, Any]:
    """Upload a document and add it to the store."""
    client = openai_client()
    file_id = client.upload_file(content, filename)
    result = client.add_file_to_vector_store(store.id, file_id)
    CacheInvalidator.invalidate_vector_store_cache()
    return {
        "file_id": file_id,
        "filename": filename,
        "status": "uploaded",
        "vector_store_file": result,
    }


def remove_file(store: VectorStore, file_id: str) -> str:
    """Take the file out of the store and delete it at OpenAI."""
    client = openai_client()
    try:
        client.remove_file_from_vector_store(store.id, file_id)
        client.delete_file(file_id)
    except Exception as error:
        if _gone(error):
            return "File was already deleted"
        raise
    CacheInvalidator.invalidate_vector_store_cache()
    return "File deleted successfully"


def file_details(file_id: str) -> dict[str, Any]:
    """What OpenAI keeps about a file (OpenAI does not give the content back)."""
    try:
        info = openai_client().get_file(file_id)
    except Exception as error:
        if _gone(error):
            raise NotFoundError("File not found") from error
        raise
    if not info:
        raise NotFoundError("File not found")
    return info


# --- Assignments to sessions -----------------------------------------------------


def _scope_filter(query: Any, dd_type_id: int | None) -> Any:
    """Narrow to one assignment scope: a DD type, or the session-wide row.

    NULL is a scope here, not a missing value: it needs IS NULL, which an
    equality would never match.
    """
    if dd_type_id is not None:
        return query.filter(col(SessionVectorStore.dd_type_id) == dd_type_id)
    return query.filter(col(SessionVectorStore.dd_type_id).is_(None))


def list_assignments(db: Session, session: DDSession) -> list[dict[str, Any]]:
    """The stores assigned to the session, each with its scope.

    The name comes from the store itself: an assigned store may be a
    colleague's, which the user's own list does not show.
    """
    rows = (
        db.query(SessionVectorStore, VectorStore, DDType)
        .join(VectorStore, col(SessionVectorStore.vector_store_id) == col(VectorStore.id))
        .outerjoin(DDType, col(SessionVectorStore.dd_type_id) == col(DDType.id))
        .filter(col(SessionVectorStore.session_id) == session.id)
        .all()
    )
    return [
        {
            "vector_store_id": store.id,
            "vector_store_name": store.name,
            "vector_store_description": store.description,
            # Both null for a session-wide assignment: every DD type of the session.
            "dd_type_id": assignment.dd_type_id,
            "dd_type_code": dd_type.code if dd_type else None,
            "assigned_at": assignment.assigned_at,
            "session_id": session.id,
        }
        for assignment, store, dd_type in rows
    ]


def _any_store(db: Session, store_id: str) -> VectorStore:
    """Any store: assignments are shared, a colleague's store can serve a session."""
    store = db.get(VectorStore, store_id)
    if store is None:
        raise NotFoundError("Vector store not found")
    return store


def assign(
    db: Session, store_id: str, session: DDSession, dd_type_id: int | None, user: User
) -> dict[str, Any]:
    """Assign a store to the session, or to one of its DD types only."""
    store = _any_store(db, store_id)
    dd_type = None
    if dd_type_id is not None:
        dd_type = db.get(DDType, dd_type_id)
        if dd_type is None:
            raise NotFoundError("DD type not found")

    existing = _scope_filter(
        db.query(SessionVectorStore).filter(
            col(SessionVectorStore.vector_store_id) == store_id,
            col(SessionVectorStore.session_id) == session.id,
        ),
        dd_type_id,
    ).first()
    if existing is not None:
        return {
            "message": "Vector store already assigned to session",
            "assignment": {
                "vector_store_id": store_id,
                "session_id": session.id,
                "dd_type_id": dd_type_id,
                "dd_type_code": dd_type.code if dd_type else None,
                "assigned_at": existing.assigned_at,
            },
        }

    assignment = SessionVectorStore(
        vector_store_id=store_id,
        session_id=stored_id(session),
        dd_type_id=dd_type_id,
        assigned_by=stored_id(user),
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return {
        "message": "Vector store assigned to session successfully",
        "assignment": {
            "vector_store_id": store_id,
            "vector_store_name": store.name,
            "session_id": session.id,
            "session_name": session.name,
            "dd_type_id": dd_type_id,
            "dd_type_code": dd_type.code if dd_type else None,
            "assigned_at": assignment.assigned_at,
        },
    }


def unassign(db: Session, store_id: str, session: DDSession, dd_type_code: str | None) -> None:
    """Remove the assignment of the given scope: one DD type, or the whole session."""
    _any_store(db, store_id)
    dd_type_id = get_dd_type_by_code(db, dd_type_code).id if dd_type_code else None
    assignment = _scope_filter(
        db.query(SessionVectorStore).filter(
            col(SessionVectorStore.vector_store_id) == store_id,
            col(SessionVectorStore.session_id) == session.id,
        ),
        dd_type_id,
    ).first()
    if assignment is None:
        raise NotFoundError("Assignment not found")
    db.delete(assignment)
    db.commit()
