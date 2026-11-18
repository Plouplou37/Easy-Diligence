from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Text, UniqueConstraint
from sqlmodel import Field, Relationship

from app.models.base import SQLModel, timestamp_field

if TYPE_CHECKING:
    from app.models.dd_types import DDType
    from app.models.questions import DDSection
    from app.models.session import DDSession
    from app.models.user import User


class DDSummary(SQLModel, table=True):
    """A generated summary attached to a session.

    Two kinds, distinguished by section_id:
      - section_id = NULL  -> the DD-type-level synthesis (the readable report body)
      - section_id set      -> a per-section summary (shown in the PDF annex)

    One current summary per (session, dd_type, section) scope; regeneration
    overwrites the row in place. Summaries are editable by hand before export.
    """

    __tablename__ = "dd_summaries"
    __table_args__ = (
        UniqueConstraint(
            "session_id", "dd_type_id", "section_id", name="unique_session_ddtype_section_summary"
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="dd_sessions.id", ondelete="CASCADE")
    dd_type_id: int = Field(foreign_key="dd_types.id")
    # NULL = DD-type synthesis; set = a section summary
    section_id: int | None = Field(
        default=None, foreign_key="dd_sections.id", ondelete="CASCADE", index=True
    )
    summary_text: str = Field(sa_type=Text)
    # NULL = AI-generated and untouched; set = manually edited
    edited_by: int | None = Field(default=None, foreign_key="users.id")
    generated_at: datetime | None = timestamp_field()
    updated_at: datetime | None = timestamp_field(updated=True)

    session: Optional["DDSession"] = Relationship()
    dd_type: Optional["DDType"] = Relationship()
    section: Optional["DDSection"] = Relationship()
    editor: Optional["User"] = Relationship()


class DDSummaryBatch(SQLModel, table=True):
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
    __table_args__ = (
        UniqueConstraint("session_id", "dd_type_id", name="unique_session_ddtype_summary_batch"),
    )

    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="dd_sessions.id", ondelete="CASCADE")
    dd_type_id: int = Field(foreign_key="dd_types.id")
    # OpenAI identifiers
    openai_batch_id: str = Field(max_length=255, index=True)
    input_file_id: str | None = Field(default=None, max_length=255)
    output_file_id: str | None = Field(default=None, max_length=255)
    # OpenAI's own status (validating, in_progress, completed, failed,
    # expired, cancelled), plus 'collected' once the results have been stored.
    status: str = Field(default="validating", max_length=50)
    error_message: str | None = Field(default=None, sa_type=Text)
    created_by: int | None = Field(default=None, foreign_key="users.id")
    created_at: datetime | None = timestamp_field()
    updated_at: datetime | None = timestamp_field(updated=True)

    session: Optional["DDSession"] = Relationship()
    dd_type: Optional["DDType"] = Relationship()
