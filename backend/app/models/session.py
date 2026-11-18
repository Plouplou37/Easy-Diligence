import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class SessionStatus(str, enum.Enum):
    CREATED = "created"
    DOCUMENTS_UPLOADED = "documents_uploaded"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class DDSession(Base):
    __tablename__ = "dd_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_code = Column(
        String(50), unique=True, index=True, nullable=True
    )  # Unique session identifier
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(SessionStatus), default=SessionStatus.CREATED)
    created_by = Column(
        Integer, ForeignKey("users.id"), nullable=True
    )  # User who created the session
    assigned_to = Column(
        Integer, ForeignKey("users.id"), nullable=True
    )  # User assigned to work on it

    # DD type versioning - Sessions are bound to specific DD type configurations
    # This ensures session isolation when DD types evolve
    dd_types_json = Column(
        Text, nullable=True
    )  # JSON array of selected DD type IDs for this session

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    company = relationship("Company", back_populates="sessions")
    answers = relationship("DDAnswer", back_populates="session")
    creator = relationship("User", back_populates="sessions_created", foreign_keys=[created_by])
    assignee = relationship("User", back_populates="sessions_assigned", foreign_keys=[assigned_to])
    executions = relationship("DDExecution", back_populates="session", cascade="all, delete-orphan")
