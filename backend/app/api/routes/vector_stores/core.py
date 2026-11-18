"""
Vector Store Core CRUD Operations
Basic create, read, update, delete functionality
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.vector_store import VectorStore
from app.models.user import User
from app.api.deps import get_current_active_user
from app.services.authz import user_is_admin
from app.engine.openai_client import OpenAIProcessor
from app.schemas.vector_stores import VectorStoreCreate, VectorStoreUpdate, VectorStoreResponse
from app.core.cache import cache_response, CacheInvalidator
from typing import List
from datetime import datetime
import logging
import asyncio

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=List[VectorStoreResponse])
@cache_response(prefix="vector_stores", ttl=300, user_specific=True)
async def list_vector_stores(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List vector stores visible to the current user (admins see all).

    Each store is enriched with live OpenAI status in parallel. Stores that no
    longer exist in OpenAI (404) or have expired are removed from the database
    to keep MySQL in sync with OpenAI, and are excluded from the response.
    """
    query = db.query(VectorStore)
    # Per-user isolation: non-admins only see vector stores they created
    if not user_is_admin(current_user):
        query = query.filter(VectorStore.created_by == current_user.id)
    vector_stores = query.order_by(VectorStore.created_at.desc()).all()

    if not vector_stores:
        return []

    openai_processor = OpenAIProcessor()

    async def _fetch(store):
        try:
            info = await openai_processor.get_vector_store_info(store.id)
            return store, info, None
        except Exception as e:
            return store, None, e

    results = await asyncio.gather(*[_fetch(store) for store in vector_stores])

    response = []
    stale_ids = []  # gone (404) or expired -> remove from DB to stay in sync
    for store, info, error in results:
        if error is not None:
            if "404" in str(error):
                stale_ids.append(store.id)
                continue
            # Other OpenAI errors: keep the store visible with an error status
            logger.warning(f"OpenAI error for vector store {store.id}: {error}")
            response.append(VectorStoreResponse(
                id=store.id,
                name=store.name,
                description=store.description,
                created_at=store.created_at,
                updated_at=store.updated_at,
                created_by=store.created_by,
                file_count=0,
                status="error",
                total_bytes=0,
            ))
            continue

        store_status = info.get("status", "unknown")
        if store_status == "expired":
            # Expired in OpenAI -> sync: drop from DB and hide from the list
            stale_ids.append(store.id)
            continue

        response.append(VectorStoreResponse(
            id=store.id,
            name=store.name,
            description=store.description,
            created_at=store.created_at,
            updated_at=store.updated_at,
            created_by=store.created_by,
            file_count=info.get("file_counts", {}).get("total", 0),
            status=store_status,
            total_bytes=info.get("usage_bytes", 0),
            expires_at=info.get("expires_at"),
            expires_after_days=info.get("expires_after_days"),
            last_active_at=info.get("last_active_at"),
        ))

    # Remove stale rows (deleted or expired in OpenAI) to keep MySQL in sync
    if stale_ids:
        from app.models.vector_store import SessionVectorStore
        db.query(SessionVectorStore).filter(
            SessionVectorStore.vector_store_id.in_(stale_ids)
        ).delete(synchronize_session=False)
        db.query(VectorStore).filter(
            VectorStore.id.in_(stale_ids)
        ).delete(synchronize_session=False)
        db.commit()
        CacheInvalidator.invalidate_vector_store_cache()
        logger.info(f"Removed {len(stale_ids)} stale vector store(s) during sync")

    return response


@router.post("/", response_model=VectorStoreResponse)
async def create_vector_store(
    vector_store: VectorStoreCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new vector store"""
    try:
        openai_processor = OpenAIProcessor()
        
        # Create in OpenAI first
        openai_store_id = await openai_processor.create_vector_store(
            name=vector_store.name,
            expires_after_days=30
        )
        
        # Create in database
        db_vector_store = VectorStore(
            id=openai_store_id,
            name=vector_store.name,
            description=vector_store.description,
            created_by=current_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(db_vector_store)
        db.commit()
        db.refresh(db_vector_store)

        # Invalidate cache
        CacheInvalidator.invalidate_vector_store_cache()

        return VectorStoreResponse(
            id=db_vector_store.id,
            name=db_vector_store.name,
            description=db_vector_store.description,
            created_at=db_vector_store.created_at,
            updated_at=db_vector_store.updated_at,
            created_by=db_vector_store.created_by,
            file_count=0,
            status="completed",
            total_bytes=0
        )
        
    except Exception as e:
        db.rollback()
        logger.exception("Failed to create vector store")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create vector store"
        )


@router.get("/{vector_store_id}", response_model=VectorStoreResponse)
async def get_vector_store(
    vector_store_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific vector store"""
    vector_store = db.query(VectorStore).filter(
        VectorStore.id == vector_store_id
    ).first()

    if not vector_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vector store not found"
        )

    # Per-user isolation: non-admins can only view their own vector stores
    if not user_is_admin(current_user) and vector_store.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vector store not found"
        )

    try:
        openai_processor = OpenAIProcessor()
        openai_store = await openai_processor.get_vector_store_info(vector_store_id)

        return VectorStoreResponse(
            id=vector_store.id,
            name=vector_store.name,
            description=vector_store.description,
            created_at=vector_store.created_at,
            updated_at=vector_store.updated_at,
            created_by=vector_store.created_by,
            file_count=openai_store.get("file_counts", {}).get("total", 0),
            status=openai_store.get("status", "unknown"),
            total_bytes=openai_store.get("usage_bytes", 0),
            expires_at=openai_store.get("expires_at"),
            expires_after_days=openai_store.get("expires_after_days"),
            last_active_at=openai_store.get("last_active_at")
        )

    except Exception as e:
        logger.error(f"Error fetching vector store {vector_store_id}: {str(e)}")

        if "404" in str(e):
            # Store exists in DB but not OpenAI - clean up
            db.delete(vector_store)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vector store no longer exists"
            )

        # For other errors (like OpenAI 500), return DB data with error status
        logger.warning(f"Returning DB data for store {vector_store_id} due to OpenAI error")
        return VectorStoreResponse(
            id=vector_store.id,
            name=vector_store.name,
            description=vector_store.description,
            created_at=vector_store.created_at,
            updated_at=vector_store.updated_at,
            created_by=vector_store.created_by,
            file_count=0,
            status="error",
            total_bytes=0,
            expires_at=None,
            expires_after_days=None,
            last_active_at=None
        )


@router.patch("/{vector_store_id}", response_model=VectorStoreResponse)
async def update_vector_store(
    vector_store_id: str,
    update_data: VectorStoreUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a vector store"""
    vector_store = db.query(VectorStore).filter(
        VectorStore.id == vector_store_id
    ).first()

    # Per-user isolation: only the owner (or an admin) may modify/delete
    if not vector_store or (
        not user_is_admin(current_user) and vector_store.created_by != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vector store not found"
        )
    
    try:
        openai_processor = OpenAIProcessor()
        
        # Update in OpenAI if name is being changed
        if update_data.name and update_data.name != vector_store.name:
            await openai_processor.modify_vector_store(
                vector_store_id, 
                name=update_data.name
            )
        
        # Update in database
        if update_data.name:
            vector_store.name = update_data.name
        if update_data.description is not None:
            vector_store.description = update_data.description
            
        vector_store.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(vector_store)

        # Invalidate cache
        CacheInvalidator.invalidate_vector_store_cache(vector_store_id)

        # Get current OpenAI status
        openai_store = await openai_processor.get_vector_store(vector_store_id)
        
        return VectorStoreResponse(
            id=vector_store.id,
            name=vector_store.name,
            description=vector_store.description,
            created_at=vector_store.created_at,
            updated_at=vector_store.updated_at,
            created_by=vector_store.created_by,
            file_count=openai_store.get("file_counts", {}).get("total", 0),
            status=openai_store.get("status", "unknown"),
            total_bytes=openai_store.get("usage_bytes", 0)
        )
        
    except Exception as e:
        db.rollback()
        logger.exception("Failed to update vector store")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update vector store"
        )


@router.post("/refresh")
async def refresh_vector_stores_cache(
    current_user: User = Depends(get_current_active_user)
):
    """Manually refresh all vector stores cache"""
    try:
        CacheInvalidator.invalidate_vector_store_cache()
        return {"message": "Vector stores cache cleared successfully"}
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        logger.exception("Failed to clear cache")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear cache"
        )


@router.post("/{vector_store_id}/refresh")
async def refresh_single_vector_store_cache(
    vector_store_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Manually refresh cache for a specific vector store"""
    vector_store = db.query(VectorStore).filter(
        VectorStore.id == vector_store_id
    ).first()

    if not vector_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vector store not found"
        )

    try:
        CacheInvalidator.invalidate_vector_store_cache(vector_store_id)
        return {"message": f"Cache cleared for vector store {vector_store_id}"}
    except Exception as e:
        logger.error(f"Failed to clear cache for store {vector_store_id}: {e}")
        logger.exception("Failed to clear cache")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear cache"
        )


@router.delete("/{vector_store_id}")
async def delete_vector_store(
    vector_store_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a vector store"""
    vector_store = db.query(VectorStore).filter(
        VectorStore.id == vector_store_id
    ).first()

    # Per-user isolation: only the owner (or an admin) may modify/delete
    if not vector_store or (
        not user_is_admin(current_user) and vector_store.created_by != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vector store not found"
        )
    
    try:
        openai_processor = OpenAIProcessor()
        
        # Delete from OpenAI (ignore 404s)
        try:
            await openai_processor.delete_vector_store(vector_store_id)
        except Exception as openai_error:
            if "404" not in str(openai_error):
                raise openai_error
        
        # Remove session assignments
        from app.models.vector_store import SessionVectorStore
        db.query(SessionVectorStore).filter(
            SessionVectorStore.vector_store_id == vector_store_id
        ).delete()
        
        # Delete from database
        db.delete(vector_store)
        db.commit()

        # Invalidate cache
        CacheInvalidator.invalidate_vector_store_cache(vector_store_id)

        return {"message": "Vector store deleted successfully"}
        
    except Exception as e:
        db.rollback()
        logger.exception("Failed to delete vector store")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete vector store"
        )