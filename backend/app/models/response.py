from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import JSON
from app.core.database import Base

class DDResponse(Base):
    __tablename__ = "dd_responses"
    
    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("dd_executions.id", ondelete="CASCADE"), nullable=False)
    response_id = Column(String(255), unique=True, nullable=False)
    previous_response_id = Column(String(255), ForeignKey("dd_responses.response_id"), nullable=True)
    openai_response = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    execution = relationship("DDExecution", back_populates="responses")
    previous_response = relationship("DDResponse", remote_side=[response_id], back_populates="next_responses")
    next_responses = relationship("DDResponse", back_populates="previous_response")
    messages = relationship("DDMessage", back_populates="response", cascade="all, delete-orphan")