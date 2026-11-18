"""
Vector Store Search Functionality
Handle search operations within vector stores
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.vector_store import VectorStore
from app.models.user import User
from app.dependencies import get_current_active_user
from app.core.openai_client import OpenAIProcessor
from app.schemas.vector_stores import VectorStoreSearchRequest, VectorStoreSearchResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/{vector_store_id}/search", response_model=VectorStoreSearchResponse)
async def search_vector_store(
    vector_store_id: str,
    search_request: VectorStoreSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Search within a vector store using semantic similarity"""
    # Verify ownership
    vector_store = db.query(VectorStore).filter(
        VectorStore.id == vector_store_id,
        VectorStore.created_by == current_user.id
    ).first()
    
    if not vector_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vector store not found"
        )
    
    try:
        openai_processor = OpenAIProcessor()
        
        # Perform vector search using OpenAI
        search_results = await openai_processor.search_vector_store(
            vector_store_id=vector_store_id,
            query=search_request.query,
            limit=search_request.limit or 10,
            filter_metadata=search_request.filter if hasattr(search_request, 'filter') else None
        )
        
        return VectorStoreSearchResponse(
            query=search_request.query,
            vector_store_id=vector_store_id,
            results=search_results.get("results", []),
            total_results=len(search_results.get("results", [])),
            processing_time_ms=search_results.get("processing_time_ms", 0)
        )
        
    except Exception as e:
        # If vector store doesn't exist in OpenAI, clean up database
        if "404" in str(e):
            db.delete(vector_store)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vector store no longer exists"
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )