from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    company = Column(String(255))
    phone = Column(String(50))
    role = Column(String(50), default='analyst')  # admin, analyst, viewer
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    last_login = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    sessions_created = relationship("DDSession", back_populates="creator", foreign_keys="DDSession.created_by")
    sessions_assigned = relationship("DDSession", back_populates="assignee", foreign_keys="DDSession.assigned_to")
    companies_created = relationship("Company", back_populates="creator", foreign_keys="Company.created_by")
    companies_updated = relationship("Company", back_populates="updater", foreign_keys="Company.updated_by")

class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    access_token = Column(String(500), unique=True, nullable=False)
    refresh_token = Column(String(500), unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    ip_address = Column(String(45))  # Supports IPv6
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User")

