from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.session import DDSession, SessionStatus
from app.models.user import User
from app.api.deps import get_current_active_user
from app.engine.openai_client import OpenAIProcessor
from typing import List, Optional
import json
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()


@router.get("/session/{session_identifier}", response_model=List[dict])
async def list_documents(
    session_identifier: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List documents for a session"""
    # Try to parse as integer ID first
    try:
        session_id = int(session_identifier)
        session = db.query(DDSession).filter(DDSession.id == session_id).first()
    except ValueError:
        # Not an integer, treat as session_code
        session = db.query(DDSession).filter(DDSession.session_code == session_identifier).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check if user has access to this session
    if current_user.role != "admin" and session.created_by != current_user.id and session.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get vector stores from new assignment system
    from app.models.vector_store import SessionVectorStore
    documents = []
    
    # Get all vector store assignments for this session
    assignments = db.query(SessionVectorStore).filter(
        SessionVectorStore.session_id == session.id
    ).all()
    
    for i, assignment in enumerate(assignments):
        documents.append({
            "id": assignment.vector_store_id,
            "filename": f"Document_batch_{i+1}",
            "uploaded_at": assignment.assigned_at
        })
    
    return documents

@router.post("/session/{session_identifier}/upload/{vector_store_id}")
async def upload_documents_to_vector_store(
    session_identifier: str,
    vector_store_id: str,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Upload documents to an existing vector store for a session"""
    # Try to parse as integer ID first
    try:
        session_id = int(session_identifier)
        session = db.query(DDSession).filter(DDSession.id == session_id).first()
    except ValueError:
        # Not an integer, treat as session_code
        session = db.query(DDSession).filter(DDSession.session_code == session_identifier).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check if user has access to this session
    if current_user.role != "admin" and session.created_by != current_user.id and session.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Verify vector store exists and user has access
    from app.models.vector_store import VectorStore
    vector_store = db.query(VectorStore).filter(
        VectorStore.id == vector_store_id,
        VectorStore.created_by == current_user.id
    ).first()
    
    if not vector_store:
        raise HTTPException(status_code=404, detail="Vector store not found or access denied")
    
    openai_processor = OpenAIProcessor()
    
    try:
        # Upload files to existing vector store
        file_ids = []
        for file in files:
            content = await file.read()
            openai_file = openai_processor.upload_file_to_vector_store(
                vector_store_id=vector_store_id,
                file_content=content,
                filename=file.filename
            )
            file_ids.append(openai_file.id)
        
        # Update vector store file count
        vector_store.file_count += len(files)
        vector_store.updated_at = datetime.utcnow()
        
        # Update session status
        session.status = SessionStatus.DOCUMENTS_UPLOADED
        
        db.commit()
        
        return {
            "message": f"Successfully uploaded {len(files)} documents",
            "vector_store_id": vector_store_id,
            "file_ids": file_ids
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")