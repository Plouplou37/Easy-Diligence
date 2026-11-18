"""Vector stores: list, create, read, update, delete, and the cleanup of the
stores gone at OpenAI."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.cache import CacheInvalidator
from app.core.database import get_db
from app.models.user import User
from app.models.vector_store import VectorStoreCreate, VectorStoreResponse, VectorStoreUpdate
from app.services import vector_stores

router = APIRouter()


@router.get("/", response_model=list[VectorStoreResponse])
def list_vector_stores(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """The user's stores (an admin's: all), with their state at OpenAI. A store
    gone at OpenAI shows as "expired" or "missing" until a refresh removes it."""
    return vector_stores.list_stores(db, current_user)


@router.post("/", response_model=VectorStoreResponse)
def create_vector_store(
    data: VectorStoreCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a store at OpenAI (it expires after 30 days without use)."""
    return vector_stores.create_store(db, data, current_user)


@router.post("/refresh")
def refresh_vector_stores(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """Remove the user's stores gone at OpenAI, and clear the cached lists."""
    removed = vector_stores.purge_stale(db, current_user)
    return {"message": "Vector stores refreshed", "removed": removed}


@router.get("/{vector_store_id}", response_model=VectorStoreResponse)
def get_vector_store(
    vector_store_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """One of the user's stores, with its state at OpenAI."""
    store = vector_stores.get_owned_store(db, vector_store_id, current_user)
    return vector_stores.get_store(db, store)


@router.patch("/{vector_store_id}", response_model=VectorStoreResponse)
def update_vector_store(
    vector_store_id: str,
    data: VectorStoreUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Rename a store, or change its description."""
    store = vector_stores.get_owned_store(db, vector_store_id, current_user)
    return vector_stores.update_store(db, store, data)


@router.post("/{vector_store_id}/refresh")
def refresh_vector_store(
    vector_store_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Clear the cached data of a store, read again from OpenAI next time."""
    vector_stores.get_owned_store(db, vector_store_id, current_user)
    CacheInvalidator.invalidate_vector_store_cache()
    return {"message": f"Cache cleared for vector store {vector_store_id}"}


@router.delete("/{vector_store_id}")
def delete_vector_store(
    vector_store_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a store, at OpenAI and here, with its assignments."""
    store = vector_stores.get_owned_store(db, vector_store_id, current_user)
    vector_stores.delete_store(db, store)
    return {"message": "Vector store deleted successfully"}
