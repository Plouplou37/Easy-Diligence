from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class DDSummary(Base):
    """A generated summary attached to a session.

    Two kinds, distinguished by section_id:
      - section_id = NULL  -> the DD-type-level synthesis (the readable report body)
      - section_id set      -> a per-section summary (shown in the PDF annex)

    One current summary per (session, dd_type, section) scope; regeneration
    overwrites the row in place. Summaries are editable by hand before export.
    """
    __tablename__ = "dd_summaries"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("dd_sessions.id", ondelete="CASCADE"), nullable=False)
    dd_type_id = Column(Integer, ForeignKey("dd_types.id"), nullable=False)
    # NULL = DD-type synthesis; set = a section summary
    section_id = Column(Integer, ForeignKey("dd_sections.id", ondelete="CASCADE"), nullable=True)
    summary_text = Column(Text, nullable=False)
    # NULL = AI-generated and untouched; set = manually edited
    edited_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    session = relationship("DDSession")
    dd_type = relationship("DDType")
    section = relationship("DDSection")
    editor = relationship("User")

    __table_args__ = (
        UniqueConstraint("session_id", "dd_type_id", "section_id", name="unique_session_ddtype_section_summary"),
    )


class DDSummaryBatch(Base):
    """An OpenAI Batch job producing the section summaries of one (session, DD type).

    Batch bills at half the synchronous rate but its only completion window is
    24h, so the job outlives any request -- and BackgroundTasks are in-process
    and do not survive a restart. The state therefore lives here, and the
    frontend polls it; nothing is lost if the server goes down meanwhile.

    Only the section summaries go through Batch. The final synthesis is derived
    from them, so it stays a synchronous call made when the batch is collected,
    rather than chaining a second 24h window.

    One row per (session, dd_type): relaunching replaces the previous job.
    """
    __tablename__ = "dd_summary_batches"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("dd_sessions.id", ondelete="CASCADE"), nullable=False)
    dd_type_id = Column(Integer, ForeignKey("dd_types.id"), nullable=False)
    # OpenAI identifiers
    openai_batch_id = Column(String(255), nullable=False, index=True)
    input_file_id = Column(String(255), nullable=True)
    output_file_id = Column(String(255), nullable=True)
    # OpenAI's own status (validating, in_progress, completed, failed,
    # expired, cancelled), plus 'collected' once the results have been stored.
    status = Column(String(50), nullable=False, default="validating")
    error_message = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    session = relationship("DDSession")
    dd_type = relationship("DDType")

    __table_args__ = (
        UniqueConstraint("session_id", "dd_type_id", name="unique_session_ddtype_summary_batch"),
    )
