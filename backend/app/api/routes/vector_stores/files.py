"""The files of a vector store: list, upload, delete, details."""

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.api.uploads import read_upload
from app.core.database import get_db
from app.models.user import User
from app.services import vector_stores

router = APIRouter()


@router.get("/{vector_store_id}/files")
def list_vector_store_files(
    vector_store_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """The files of one of the user's stores."""
    store = vector_stores.get_owned_store(db, vector_store_id, current_user)
    return {"files": vector_stores.list_files(store)}


@router.post("/{vector_store_id}/files")
async def upload_file_to_vector_store(
    vector_store_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Add a document to one of the user's stores."""
    store = vector_stores.get_owned_store(db, vector_store_id, current_user)
    content = await read_upload(file)
    return await run_in_threadpool(vector_stores.add_file, store, content, file.filename or "")


@router.delete("/{vector_store_id}/files/{file_id}")
def delete_file_from_vector_store(
    vector_store_id: str,
    file_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Take a file out of a store and delete it at OpenAI."""
    store = vector_stores.get_owned_store(db, vector_store_id, current_user)
    return {"message": vector_stores.remove_file(store, file_id)}


@router.get("/{vector_store_id}/files/{file_id}/content")
def get_file_content(
    vector_store_id: str,
    file_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """What OpenAI keeps about a file of the store."""
    vector_stores.get_owned_store(db, vector_store_id, current_user)
    info = vector_stores.file_details(file_id)
    response = {
        "file_id": file_id,
        "filename": info.get("filename", "unknown"),
        "bytes": info.get("bytes", 0),
        "status": info.get("status", "unknown"),
        "purpose": info.get("purpose", "unknown"),
        "created_at": info.get("created_at"),
        "message": "File content processing is handled by OpenAI vector store",
    }
    if info.get("expires_at"):
        response["expires_at"] = info["expires_at"]
    return response


@router.get("/{vector_store_id}/files/{file_id}/original")
def download_original_file(
    vector_store_id: str,
    file_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """OpenAI does not give a file's content back: its details only."""
    vector_stores.get_owned_store(db, vector_store_id, current_user)
    info = vector_stores.file_details(file_id)
    file_info = {
        "filename": info.get("filename", "unknown"),
        "bytes": info.get("bytes", 0),
        "status": info.get("status", "unknown"),
        "created_at": info.get("created_at"),
    }
    if info.get("expires_at"):
        file_info["expires_at"] = info["expires_at"]
    return {"message": "Original file download not supported by OpenAI API", "file_info": file_info}
