from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

# Shown on the DD card. The import used to default to the literal string
# "[DD]", which is truthy and so slipped past the frontend's own emoji
# fallback: the card rendered the four characters in place of an icon.
DEFAULT_DD_TYPE_ICON = "📋"


class DDType(Base):
    __tablename__ = "dd_types"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(10), nullable=True)  # Store emoji or icon reference
    is_active = Column(Boolean, default=True)
    is_system = Column(Boolean, default=False)  # System types can't be deleted
    is_validated = Column(Boolean, default=False)  # DD type validation status
    order_index = Column(Integer, default=0)
    # Owner of this DD type. NULL = shared (system templates visible to everyone).
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships (direct to sections, progress)
    sections = relationship("DDSection", back_populates="dd_type_obj", cascade="all, delete-orphan")
    executions = relationship("DDExecution", back_populates="dd_type")
    creator = relationship("User")