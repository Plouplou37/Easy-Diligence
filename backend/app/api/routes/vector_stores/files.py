"""
Vector Store File Management
Handle file upload, deletion, and content retrieval
"""
import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.api.uploads import read_upload
from app.core.cache import CacheInvalidator, cache_response
from app.core.database import get_db
from app.engine.openai_client import OpenAIProcessor
from app.models.user import User
from app.models.vector_store import VectorStore
from app.services.authz import user_is_admin

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_owned_vector_store(vector_store_id: str, db: Session, current_user: User) -> VectorStore:
    """Load a vector store, enforcing per-user isolation (admins see all).

    Raises 404 if it doesn't exist or isn't owned by the user (404 rather than
    403 so other users' store ids are not enumerable).
    """
    vector_store = db.query(VectorStore).filter(
        VectorStore.id == vector_store_id
    ).first()
    if not vector_store or (
        not user_is_admin(current_user) and vector_store.created_by != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vector store not found"
        )
    return vector_store


@router.get("/{vector_store_id}/files")
@cache_response(prefix="vector_store_files", ttl=300, key_params=["vector_store_id"], user_specific=True)
async def list_vector_store_files(
    vector_store_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List files in a vector store"""
    vector_store = _get_owned_vector_store(vector_store_id, db, current_user)

    try:
        openai_processor = OpenAIProcessor()
        files = await openai_processor.list_vector_store_files(vector_store_id)
        return {"files": files}
    except Exception as e:
        # If vector store doesn't exist in OpenAI, clean up database
        if "404" in str(e):
            # Remove session assignments first to avoid FK constraint
            from app.models.vector_store import SessionVectorStore
            db.query(SessionVectorStore).filter(
                SessionVectorStore.vector_store_id == vector_store_id
            ).delete()
            db.delete(vector_store)
            db.commit()
            raise HTTPException(  # noqa: B904
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vector store no longer exists"
            )
        logger.exception("Failed to list files")
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list files"
        )


@router.post("/{vector_store_id}/files")
async def upload_file_to_vector_store(
    vector_store_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Upload a file to a vector store"""
    _get_owned_vector_store(vector_store_id, db, current_user)
    file_content = await read_upload(file)

    try:
        openai_processor = OpenAIProcessor()

        # Upload and add to vector store
        file_id = await openai_processor.upload_file(file_content, file.filename)
        result = await openai_processor.add_file_to_vector_store(vector_store_id, file_id)

        # Invalidate cache for this vector store
        CacheInvalidator.invalidate_vector_store_cache(vector_store_id)

        return {
            "file_id": file_id,
            "filename": file.filename,
            "status": "uploaded",
            "vector_store_file": result
        }

    except Exception:
        logger.exception("Failed to upload file")
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file"
        )


@router.delete("/{vector_store_id}/files/{file_id}")
async def delete_file_from_vector_store(
    vector_store_id: str,
    file_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a file from a vector store"""
    _get_owned_vector_store(vector_store_id, db, current_user)

    try:
        openai_processor = OpenAIProcessor()

        # Remove from vector store and delete file
        await openai_processor.remove_file_from_vector_store(vector_store_id, file_id)
        await openai_processor.delete_file(file_id)

        # Invalidate cache for this vector store
        CacheInvalidator.invalidate_vector_store_cache(vector_store_id)

        return {"message": "File deleted successfully"}

    except Exception as e:
        # If file is already gone, that's fine
        if "404" in str(e):
            return {"message": "File was already deleted"}
        logger.exception("Failed to delete file")
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file"
        )


@router.get("/{vector_store_id}/files/{file_id}/content")
async def get_file_content(
    vector_store_id: str,
    file_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get processed content of a file (for preview)"""
    _get_owned_vector_store(vector_store_id, db, current_user)

    try:
        openai_processor = OpenAIProcessor()

        # Get file info first
        file_info = await openai_processor.get_file(file_id)
        if not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )

        # Return file info including expiration
        response = {
            "file_id": file_id,
            "filename": file_info.get("filename", "unknown"),
            "bytes": file_info.get("bytes", 0),
            "status": file_info.get("status", "unknown"),
            "purpose": file_info.get("purpose", "unknown"),
            "created_at": file_info.get("created_at"),
            "message": "File content processing is handled by OpenAI vector store"
        }

        # Include expiration if set
        if file_info.get("expires_at"):
            response["expires_at"] = file_info["expires_at"]

        return response

    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to get file content")
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get file content"
        )


@router.get("/{vector_store_id}/files/{file_id}/original")
async def download_original_file(
    vector_store_id: str,
    file_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Download original file content"""
    _get_owned_vector_store(vector_store_id, db, current_user)

    try:
        openai_processor = OpenAIProcessor()

        # Get file info and content
        file_info = await openai_processor.get_file(file_id)
        if not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )

        # OpenAI doesn't typically allow downloading original content
        # for vector store files for security reasons
        response = {
            "message": "Original file download not supported by OpenAI API",
            "file_info": {
                "filename": file_info.get("filename", "unknown"),
                "bytes": file_info.get("bytes", 0),
                "status": file_info.get("status", "unknown"),
                "created_at": file_info.get("created_at")
            }
        }

        # Include expiration if set
        if file_info.get("expires_at"):
            response["file_info"]["expires_at"] = file_info["expires_at"]

        return response

    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to download file")
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download file"
        )
