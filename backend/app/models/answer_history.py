from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class DDAnswerHistory(Base):
    __tablename__ = "dd_answer_history"

    id = Column(Integer, primary_key=True, index=True)
    answer_id = Column(Integer, ForeignKey("dd_answers.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    sources = Column(JSON, nullable=True)
    edited_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    edit_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    answer = relationship("DDAnswer", back_populates="history")
    editor = relationship("User", foreign_keys=[edited_by])
