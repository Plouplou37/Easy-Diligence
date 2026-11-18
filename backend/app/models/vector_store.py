from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, BigInteger, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class VectorStore(Base):
    __tablename__ = "vector_stores"
    
    # Minimal tracking - all metadata fetched from OpenAI API
    id = Column(String(255), primary_key=True, index=True)  # OpenAI vector store ID
    name = Column(String(255), nullable=False)  # Vector store name
    description = Column(Text, nullable=True)  # Our custom field (not in OpenAI)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # Ownership tracking
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # Our record tracking
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())  # Our record tracking
    
    # Relationships
    creator = relationship("User")
    session_assignments = relationship("SessionVectorStore", back_populates="vector_store")

class SessionVectorStore(Base):
    __tablename__ = "session_vector_stores"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("dd_sessions.id", ondelete="CASCADE"), nullable=False)
    dd_type_id = Column(Integer, nullable=True)  # NULL = whole session, specific ID = DD type only
    vector_store_id = Column(String(255), ForeignKey("vector_stores.id"), nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationships
    session = relationship("DDSession")
    vector_store = relationship("VectorStore", back_populates="session_assignments")
    assignee = relationship("User")
    
    # Constraints: unique assignment per session/dd_type combination
    __table_args__ = (
        # This ensures no duplicate assignments
        # Either session-wide (dd_type_code IS NULL) or dd_type-specific
        # UniqueConstraint('session_id', 'dd_type_code', name='unique_session_dd_type_vector_store')
    )