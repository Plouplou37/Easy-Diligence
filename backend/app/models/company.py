from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Company(Base):
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    # The DD subject: the fund / product under review.
    name = Column(String(255), nullable=False, index=True)
    website_url = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)

    # The company running that fund. Kept apart from `name` so the engine can
    # tell the model which entity a question is about instead of guessing --
    # web search quality depends on it. NULL when unknown.
    management_company_name = Column(String(255), nullable=True)
    management_company_website = Column(String(500), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    sessions = relationship("DDSession", back_populates="company")
    creator = relationship("User", foreign_keys=[created_by], back_populates="companies_created")
    updater = relationship("User", foreign_keys=[updated_by])