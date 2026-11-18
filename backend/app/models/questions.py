from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class DDSection(Base):
    __tablename__ = "dd_sections"

    id = Column(Integer, primary_key=True, index=True)
    dd_type_id = Column(Integer, ForeignKey("dd_types.id"), nullable=False)
    section_code = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    order_index = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    dd_type_obj = relationship("DDType", back_populates="sections")
    questions = relationship("DDQuestion", back_populates="section", cascade="all, delete-orphan")

class DDQuestion(Base):
    __tablename__ = "dd_questions"

    id = Column(Integer, primary_key=True, index=True)
    section_id = Column(Integer, ForeignKey("dd_sections.id"), nullable=False)
    question_code = Column(String(50), nullable=False)
    question_text = Column(Text, nullable=False)
    context_prompt = Column(Text, nullable=True)
    order_index = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    section = relationship("DDSection", back_populates="questions")