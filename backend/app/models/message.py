from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import JSON
from app.database import Base

class DDMessage(Base):
    __tablename__ = "dd_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    response_id = Column(String(255), ForeignKey("dd_responses.response_id", ondelete="CASCADE"), nullable=False)
    message_index = Column(Integer, nullable=False)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=True)
    tool_calls = Column(JSON, nullable=True)
    openai_message_id = Column(String(255), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    response = relationship("DDResponse", back_populates="messages")
    
    # Ensure unique message index per response
    __table_args__ = (
        UniqueConstraint('response_id', 'message_index', name='uq_message_response_index'),
    )