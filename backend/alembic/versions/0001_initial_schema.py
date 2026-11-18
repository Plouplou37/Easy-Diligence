"""initial schema

The whole schema from scratch: generated from the models, then reviewed.
It replaces create_all() and the SQL fixes once applied by hand to the old
MySQL database; their final state (indexes, cascades, check constraints) is
declared in the models and therefore included here.

Revision ID: 0001
Revises:
Create Date: 2026-11-18 16:47:58.948008

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("username", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("password_hash", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("full_name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("company", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("phone", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True),
        sa.Column("role", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=True),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("website_url", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "management_company_name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True
        ),
        sa.Column(
            "management_company_website",
            sqlmodel.sql.sqltypes.AutoString(length=500),
            nullable=True,
        ),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name=op.f("fk_companies_created_by_users")
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"], ["users.id"], name=op.f("fk_companies_updated_by_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_companies")),
    )
    op.create_index(op.f("ix_companies_created_by"), "companies", ["created_by"], unique=False)
    op.create_index(op.f("ix_companies_name"), "companies", ["name"], unique=False)
    op.create_index(op.f("ix_companies_updated_by"), "companies", ["updated_by"], unique=False)
    op.create_table(
        "dd_types",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sqlmodel.sql.sqltypes.AutoString(length=10), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=True),
        sa.Column("is_validated", sa.Boolean(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name=op.f("fk_dd_types_created_by_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dd_types")),
    )
    op.create_index(op.f("ix_dd_types_code"), "dd_types", ["code"], unique=True)
    op.create_index(op.f("ix_dd_types_created_by"), "dd_types", ["created_by"], unique=False)
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("access_token_hash", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("refresh_token_hash", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip_address", sqlmodel.sql.sqltypes.AutoString(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_sessions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_sessions")),
        sa.UniqueConstraint("access_token_hash", name=op.f("uq_user_sessions_access_token_hash")),
        sa.UniqueConstraint("refresh_token_hash", name=op.f("uq_user_sessions_refresh_token_hash")),
    )
    op.create_index(op.f("ix_user_sessions_user_id"), "user_sessions", ["user_id"], unique=False)
    op.create_table(
        "vector_stores",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name=op.f("fk_vector_stores_created_by_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_vector_stores")),
    )
    op.create_index(
        op.f("ix_vector_stores_created_by"), "vector_stores", ["created_by"], unique=False
    )
    op.create_table(
        "dd_sections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dd_type_id", sa.Integer(), nullable=False),
        sa.Column("section_code", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("title", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.CheckConstraint("order_index >= 0", name=op.f("ck_dd_sections_order_non_negative")),
        sa.ForeignKeyConstraint(
            ["dd_type_id"], ["dd_types.id"], name=op.f("fk_dd_sections_dd_type_id_dd_types")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dd_sections")),
    )
    op.create_index(
        "ix_dd_sections_dd_type_order", "dd_sections", ["dd_type_id", "order_index"], unique=False
    )
    op.create_table(
        "dd_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_code", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "CREATED",
                "DOCUMENTS_UPLOADED",
                "IN_PROGRESS",
                "COMPLETED",
                "FAILED",
                "PAUSED",
                name="session_status",
                native_enum=False,
                create_constraint=True,
                length=50,
            ),
            nullable=True,
        ),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("assigned_to", sa.Integer(), nullable=True),
        sa.Column("dd_types_json", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["assigned_to"], ["users.id"], name=op.f("fk_dd_sessions_assigned_to_users")
        ),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"], name=op.f("fk_dd_sessions_company_id_companies")
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name=op.f("fk_dd_sessions_created_by_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dd_sessions")),
    )
    op.create_index(
        op.f("ix_dd_sessions_assigned_to"), "dd_sessions", ["assigned_to"], unique=False
    )
    op.create_index(
        "ix_dd_sessions_company_status", "dd_sessions", ["company_id", "status"], unique=False
    )
    op.create_index(op.f("ix_dd_sessions_created_by"), "dd_sessions", ["created_by"], unique=False)
    op.create_index(
        op.f("ix_dd_sessions_session_code"), "dd_sessions", ["session_code"], unique=True
    )
    op.create_table(
        "dd_executions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("dd_type_id", sa.Integer(), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True),
        sa.Column("conversation_id", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("validator_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["dd_type_id"],
            ["dd_types.id"],
            name=op.f("fk_dd_executions_dd_type_id_dd_types"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["dd_sessions.id"],
            name=op.f("fk_dd_executions_session_id_dd_sessions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["validator_id"], ["users.id"], name=op.f("fk_dd_executions_validator_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dd_executions")),
        sa.UniqueConstraint("conversation_id", name=op.f("uq_dd_executions_conversation_id")),
    )
    op.create_index(
        op.f("ix_dd_executions_dd_type_id"), "dd_executions", ["dd_type_id"], unique=False
    )
    op.create_index(
        "ix_dd_executions_session_status", "dd_executions", ["session_id", "status"], unique=False
    )
    op.create_table(
        "dd_questions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("section_id", sa.Integer(), nullable=False),
        sa.Column("question_code", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("context_prompt", sa.Text(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.CheckConstraint("order_index >= 0", name=op.f("ck_dd_questions_order_non_negative")),
        sa.ForeignKeyConstraint(
            ["section_id"], ["dd_sections.id"], name=op.f("fk_dd_questions_section_id_dd_sections")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dd_questions")),
    )
    op.create_index(
        "ix_dd_questions_section_order", "dd_questions", ["section_id", "order_index"], unique=False
    )
    op.create_table(
        "dd_summaries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("dd_type_id", sa.Integer(), nullable=False),
        sa.Column("section_id", sa.Integer(), nullable=True),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("edited_by", sa.Integer(), nullable=True),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["dd_type_id"], ["dd_types.id"], name=op.f("fk_dd_summaries_dd_type_id_dd_types")
        ),
        sa.ForeignKeyConstraint(
            ["edited_by"], ["users.id"], name=op.f("fk_dd_summaries_edited_by_users")
        ),
        sa.ForeignKeyConstraint(
            ["section_id"],
            ["dd_sections.id"],
            name=op.f("fk_dd_summaries_section_id_dd_sections"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["dd_sessions.id"],
            name=op.f("fk_dd_summaries_session_id_dd_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dd_summaries")),
        sa.UniqueConstraint(
            "session_id", "dd_type_id", "section_id", name="unique_session_ddtype_section_summary"
        ),
    )
    op.create_index(
        op.f("ix_dd_summaries_section_id"), "dd_summaries", ["section_id"], unique=False
    )
    op.create_table(
        "dd_summary_batches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("dd_type_id", sa.Integer(), nullable=False),
        sa.Column("openai_batch_id", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("input_file_id", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("output_file_id", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name=op.f("fk_dd_summary_batches_created_by_users")
        ),
        sa.ForeignKeyConstraint(
            ["dd_type_id"], ["dd_types.id"], name=op.f("fk_dd_summary_batches_dd_type_id_dd_types")
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["dd_sessions.id"],
            name=op.f("fk_dd_summary_batches_session_id_dd_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dd_summary_batches")),
        sa.UniqueConstraint("session_id", "dd_type_id", name="unique_session_ddtype_summary_batch"),
    )
    op.create_index(
        op.f("ix_dd_summary_batches_openai_batch_id"),
        "dd_summary_batches",
        ["openai_batch_id"],
        unique=False,
    )
    op.create_table(
        "session_vector_stores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("dd_type_id", sa.Integer(), nullable=True),
        sa.Column("vector_store_id", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column("assigned_by", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["assigned_by"], ["users.id"], name=op.f("fk_session_vector_stores_assigned_by_users")
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["dd_sessions.id"],
            name=op.f("fk_session_vector_stores_session_id_dd_sessions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["vector_store_id"],
            ["vector_stores.id"],
            name=op.f("fk_session_vector_stores_vector_store_id_vector_stores"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_session_vector_stores")),
    )
    op.create_index(
        op.f("ix_session_vector_stores_session_id"),
        "session_vector_stores",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_session_vector_stores_vector_store_id"),
        "session_vector_stores",
        ["vector_store_id"],
        unique=False,
    )
    op.create_table(
        "dd_responses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("execution_id", sa.Integer(), nullable=False),
        sa.Column("response_id", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column(
            "previous_response_id", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True
        ),
        sa.Column(
            "openai_response",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["execution_id"],
            ["dd_executions.id"],
            name=op.f("fk_dd_responses_execution_id_dd_executions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["previous_response_id"],
            ["dd_responses.response_id"],
            name=op.f("fk_dd_responses_previous_response_id_dd_responses"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dd_responses")),
        sa.UniqueConstraint("response_id", name=op.f("uq_dd_responses_response_id")),
    )
    op.create_index(
        op.f("ix_dd_responses_execution_id"), "dd_responses", ["execution_id"], unique=False
    )
    op.create_index(
        op.f("ix_dd_responses_previous_response_id"),
        "dd_responses",
        ["previous_response_id"],
        unique=False,
    )
    op.create_table(
        "dd_answers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("execution_id", sa.Integer(), nullable=True),
        sa.Column("section_code", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("question_code", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("section_id", sa.Integer(), nullable=True),
        sa.Column("question_id", sa.Integer(), nullable=True),
        sa.Column("dd_type_id", sa.Integer(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "COMPLETED",
                "FAILED",
                "DRAFT",
                "NEEDS_REVIEW",
                "APPROVED",
                "REJECTED",
                name="answer_status",
                native_enum=False,
                create_constraint=True,
                length=50,
            ),
            nullable=True,
        ),
        sa.Column("edited_by", sa.Integer(), nullable=True),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("answer_text", sa.Text(), nullable=True),
        sa.Column(
            "sources",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("response_id", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=True),
        sa.Column(
            "error_type",
            sa.Enum(
                "rate_limit",
                "context_overflow",
                "api_error",
                "network_error",
                "validation_error",
                "timeout",
                "unknown",
                name="error_type",
                native_enum=False,
                create_constraint=True,
                length=50,
            ),
            nullable=True,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name=op.f("ck_dd_answers_confidence_range"),
        ),
        sa.CheckConstraint("tokens_used >= 0", name=op.f("ck_dd_answers_tokens_non_negative")),
        sa.ForeignKeyConstraint(
            ["dd_type_id"], ["dd_types.id"], name=op.f("fk_dd_answers_dd_type_id_dd_types")
        ),
        sa.ForeignKeyConstraint(
            ["edited_by"], ["users.id"], name=op.f("fk_dd_answers_edited_by_users")
        ),
        sa.ForeignKeyConstraint(
            ["execution_id"],
            ["dd_executions.id"],
            name=op.f("fk_dd_answers_execution_id_dd_executions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["dd_questions.id"],
            name=op.f("fk_dd_answers_question_id_dd_questions"),
        ),
        sa.ForeignKeyConstraint(
            ["response_id"],
            ["dd_responses.response_id"],
            name=op.f("fk_dd_answers_response_id_dd_responses"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["section_id"], ["dd_sections.id"], name=op.f("fk_dd_answers_section_id_dd_sections")
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["dd_sessions.id"],
            name=op.f("fk_dd_answers_session_id_dd_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dd_answers")),
    )
    op.create_index(op.f("ix_dd_answers_dd_type_id"), "dd_answers", ["dd_type_id"], unique=False)
    op.create_index(
        "ix_dd_answers_execution_status", "dd_answers", ["execution_id", "status"], unique=False
    )
    op.create_index(op.f("ix_dd_answers_question_id"), "dd_answers", ["question_id"], unique=False)
    op.create_index(op.f("ix_dd_answers_response_id"), "dd_answers", ["response_id"], unique=False)
    op.create_index(op.f("ix_dd_answers_section_id"), "dd_answers", ["section_id"], unique=False)
    op.create_index(
        "ix_dd_answers_session_current_status",
        "dd_answers",
        ["session_id", "is_current", "status"],
        unique=False,
    )
    op.create_table(
        "dd_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("response_id", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("message_index", sa.Integer(), nullable=False),
        sa.Column("role", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column(
            "tool_calls",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.Column("openai_message_id", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["response_id"],
            ["dd_responses.response_id"],
            name=op.f("fk_dd_messages_response_id_dd_responses"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dd_messages")),
        sa.UniqueConstraint("response_id", "message_index", name="uq_message_response_index"),
    )
    op.create_index(
        op.f("ix_dd_messages_openai_message_id"), "dd_messages", ["openai_message_id"], unique=False
    )
    op.create_table(
        "dd_answer_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("answer_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "sources",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.Column("edited_by", sa.Integer(), nullable=True),
        sa.Column("edit_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["answer_id"],
            ["dd_answers.id"],
            name=op.f("fk_dd_answer_history_answer_id_dd_answers"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["edited_by"], ["users.id"], name=op.f("fk_dd_answer_history_edited_by_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dd_answer_history")),
    )
    op.create_index(
        "ix_dd_answer_history_answer_version",
        "dd_answer_history",
        ["answer_id", "version"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_dd_answer_history_answer_version", table_name="dd_answer_history")
    op.drop_table("dd_answer_history")
    op.drop_index(op.f("ix_dd_messages_openai_message_id"), table_name="dd_messages")
    op.drop_table("dd_messages")
    op.drop_index("ix_dd_answers_session_current_status", table_name="dd_answers")
    op.drop_index(op.f("ix_dd_answers_section_id"), table_name="dd_answers")
    op.drop_index(op.f("ix_dd_answers_response_id"), table_name="dd_answers")
    op.drop_index(op.f("ix_dd_answers_question_id"), table_name="dd_answers")
    op.drop_index("ix_dd_answers_execution_status", table_name="dd_answers")
    op.drop_index(op.f("ix_dd_answers_dd_type_id"), table_name="dd_answers")
    op.drop_table("dd_answers")
    op.drop_index(op.f("ix_dd_responses_previous_response_id"), table_name="dd_responses")
    op.drop_index(op.f("ix_dd_responses_execution_id"), table_name="dd_responses")
    op.drop_table("dd_responses")
    op.drop_index(
        op.f("ix_session_vector_stores_vector_store_id"), table_name="session_vector_stores"
    )
    op.drop_index(op.f("ix_session_vector_stores_session_id"), table_name="session_vector_stores")
    op.drop_table("session_vector_stores")
    op.drop_index(op.f("ix_dd_summary_batches_openai_batch_id"), table_name="dd_summary_batches")
    op.drop_table("dd_summary_batches")
    op.drop_index(op.f("ix_dd_summaries_section_id"), table_name="dd_summaries")
    op.drop_table("dd_summaries")
    op.drop_index("ix_dd_questions_section_order", table_name="dd_questions")
    op.drop_table("dd_questions")
    op.drop_index("ix_dd_executions_session_status", table_name="dd_executions")
    op.drop_index(op.f("ix_dd_executions_dd_type_id"), table_name="dd_executions")
    op.drop_table("dd_executions")
    op.drop_index(op.f("ix_dd_sessions_session_code"), table_name="dd_sessions")
    op.drop_index(op.f("ix_dd_sessions_created_by"), table_name="dd_sessions")
    op.drop_index("ix_dd_sessions_company_status", table_name="dd_sessions")
    op.drop_index(op.f("ix_dd_sessions_assigned_to"), table_name="dd_sessions")
    op.drop_table("dd_sessions")
    op.drop_index("ix_dd_sections_dd_type_order", table_name="dd_sections")
    op.drop_table("dd_sections")
    op.drop_index(op.f("ix_vector_stores_created_by"), table_name="vector_stores")
    op.drop_table("vector_stores")
    op.drop_index(op.f("ix_user_sessions_user_id"), table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_index(op.f("ix_dd_types_created_by"), table_name="dd_types")
    op.drop_index(op.f("ix_dd_types_code"), table_name="dd_types")
    op.drop_table("dd_types")
    op.drop_index(op.f("ix_companies_updated_by"), table_name="companies")
    op.drop_index(op.f("ix_companies_name"), table_name="companies")
    op.drop_index(op.f("ix_companies_created_by"), table_name="companies")
    op.drop_table("companies")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
