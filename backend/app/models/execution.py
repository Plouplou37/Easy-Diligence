from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum

class ExecutionStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    GENERATED = "generated"
    FAILED = "failed"
    PAUSED = "paused"
    UNDER_REVIEW = "under_review"
    VALIDATED = "validated"
    FINALIZED = "finalized"

class DDExecution(Base):
    __tablename__ = "dd_executions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("dd_sessions.id", ondelete="CASCADE"), nullable=False)
    dd_type_id = Column(Integer, ForeignKey("dd_types.id", ondelete="RESTRICT"), nullable=False)
    status = Column(String(50), default=ExecutionStatus.NOT_STARTED.value)
    conversation_id = Column(String(255), unique=True, nullable=True)
    validator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    session = relationship("DDSession", back_populates="executions")
    dd_type = relationship("DDType", back_populates="executions")
    validator = relationship("User", foreign_keys="DDExecution.validator_id")
    responses = relationship("DDResponse", back_populates="execution", cascade="all, delete-orphan")
    answers = relationship("DDAnswer", back_populates="execution", cascade="all, delete-orphan")