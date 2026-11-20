"""integrity: the database enforces its own rules

The rules the code took for granted, now held by the database:
- one execution per (session, DD type);
- at most one current answer per (execution, question);
- one summary per (session, DD type, section), the synthesis (section NULL)
  included, and one assignment per (session, DD type or whole session, store),
  pointing at a DD type that exists;
- section codes unique in a DD type, question codes unique in a section;
- no boolean, status, counter or creation date left NULL, each with a default
  set by the database;
- every status checked, and stored by value, lowercase: dd_answers.status held
  the member names ('NEEDS_REVIEW').

Two NULL are distinct to SQL, so the synthesis and the whole-session assignment
get a partial unique index each, rather than NULLS NOT DISTINCT: the models
declare the same index for SQLite, where the tests run.

The data is fixed before the constraints are laid (scripts/audit_integrity.py
lists what is fixed). What calls for a decision is never fixed here: the
migration stops before any change, and says what it found.

Written by hand: autogenerate needs a PostgreSQL to compare with, and sees
neither partial indexes, nor CHECK constraints, nor data.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-20 11:06:02

"""

import logging
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

log = logging.getLogger("alembic.0002")

# The values as of this revision, not imported from the models: a migration
# stays what it was when the models move on.
EXECUTION_STATUSES = (
    "not_started",
    "in_progress",
    "generated",
    "failed",
    "paused",
    "under_review",
    "validated",
    "finalized",
)
ANSWER_STATUSES = ("completed", "failed", "draft", "needs_review", "approved", "rejected")
ROLES = ("admin", "analyst")

TIMESTAMP = sa.DateTime(timezone=True)

# Columns that become NOT NULL: (table, column, type, default). The database
# sets the default from now on, and the rows holding NULL get it first. None
# for a timestamp, which already defaults to now().
NOT_NULL: list[tuple[str, str, sa.types.TypeEngine, str | None]] = [
    ("users", "role", sa.String(50), "'analyst'"),
    ("users", "is_active", sa.Boolean(), "true"),
    ("users", "is_verified", sa.Boolean(), "false"),
    ("users", "created_at", TIMESTAMP, None),
    ("user_sessions", "created_at", TIMESTAMP, None),
    ("dd_types", "is_active", sa.Boolean(), "true"),
    ("dd_types", "is_system", sa.Boolean(), "false"),
    ("dd_types", "is_validated", sa.Boolean(), "false"),
    ("dd_types", "order_index", sa.Integer(), "0"),
    ("dd_types", "created_at", TIMESTAMP, None),
    ("dd_types", "updated_at", TIMESTAMP, None),
    ("dd_sessions", "created_at", TIMESTAMP, None),
    ("dd_sessions", "updated_at", TIMESTAMP, None),
    ("dd_executions", "status", sa.String(50), "'not_started'"),
    ("dd_executions", "created_at", TIMESTAMP, None),
    ("dd_executions", "updated_at", TIMESTAMP, None),
    ("dd_answers", "version", sa.Integer(), "1"),
    ("dd_answers", "is_current", sa.Boolean(), "true"),
    ("dd_answers", "status", sa.String(50), "'needs_review'"),
    ("dd_answers", "tokens_used", sa.Integer(), "0"),
    ("dd_answers", "retry_count", sa.Integer(), "0"),
    ("dd_answers", "created_at", TIMESTAMP, None),
    ("dd_answers", "updated_at", TIMESTAMP, None),
    ("dd_sections", "created_at", TIMESTAMP, None),
    ("dd_questions", "created_at", TIMESTAMP, None),
    ("dd_summaries", "generated_at", TIMESTAMP, None),
    ("dd_summary_batches", "created_at", TIMESTAMP, None),
    ("session_vector_stores", "assigned_at", TIMESTAMP, None),
    ("dd_responses", "created_at", TIMESTAMP, None),
    ("dd_messages", "created_at", TIMESTAMP, None),
    ("dd_answer_history", "created_at", TIMESTAMP, None),
    ("vector_stores", "created_at", TIMESTAMP, None),
]

# Keys without a default: a row missing one is not fixed by guessing.
REQUIRED_KEYS: list[tuple[str, str]] = [
    ("dd_answers", "execution_id"),
    ("dd_answers", "question_id"),
    ("user_sessions", "user_id"),
]

# (name, table, columns): unique constraints.
UNIQUE = [
    ("uq_dd_executions_session_id", "dd_executions", ["session_id", "dd_type_id"]),
    ("uq_dd_sections_dd_type_id", "dd_sections", ["dd_type_id", "section_code"]),
    ("uq_dd_questions_section_id", "dd_questions", ["section_id", "question_code"]),
    (
        "uq_session_vector_stores_session_id",
        "session_vector_stores",
        ["session_id", "dd_type_id", "vector_store_id"],
    ),
]

# (name, table, columns, condition): partial unique indexes.
PARTIAL_UNIQUE = [
    ("ix_dd_answers_one_current", "dd_answers", ["execution_id", "question_id"], "is_current"),
    (
        "ix_dd_summaries_one_synthesis",
        "dd_summaries",
        ["session_id", "dd_type_id"],
        "section_id IS NULL",
    ),
    (
        "ix_session_vector_stores_one_session_wide",
        "session_vector_stores",
        ["session_id", "vector_store_id"],
        "dd_type_id IS NULL",
    ),
]


def _in(values: Sequence[str]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _duplicates(table: str, keys: str, where: str = "true") -> str:
    """The rows sharing their `keys` with another row; NULL counts as a value,
    as PARTITION BY does."""
    return (
        f"SELECT id FROM (SELECT id, count(*) OVER (PARTITION BY {keys}) AS n "
        f"FROM {table} WHERE {where}) AS counted WHERE n > 1 ORDER BY id"
    )


# What calls for the owner's decision: (problem, query returning the row ids).
NEEDS_A_DECISION = [
    (
        "executions share their (session, DD type)",
        _duplicates("dd_executions", "session_id, dd_type_id"),
    ),
    (
        "answers have no execution or no question",
        "SELECT id FROM dd_answers WHERE execution_id IS NULL OR question_id IS NULL ORDER BY id",
    ),
    (
        "sections share their code within a DD type",
        _duplicates("dd_sections", "dd_type_id, section_code"),
    ),
    (
        "questions share their code within a section",
        _duplicates("dd_questions", "section_id, question_code"),
    ),
    (
        "executions have an unknown status",
        f"SELECT id FROM dd_executions WHERE status NOT IN ({_in(EXECUTION_STATUSES)}) ORDER BY id",
    ),
    (
        "users have an unknown role",
        f"SELECT id FROM users WHERE role NOT IN ({_in(ROLES)}) ORDER BY id",
    ),
]


def _ranked_out(table: str, keys: str, order: str, where: str = "true") -> str:
    """The ids of all the rows of each `keys` group but the first by `order`."""
    return (
        f"SELECT id FROM (SELECT id, row_number() OVER (PARTITION BY {keys} ORDER BY {order}) "
        f"AS place FROM {table} WHERE {where}) AS ranked WHERE place > 1"
    )


# What is fixed, in this order: (what, statement).
FIXES = [
    (
        "assignments to a DD type that no longer exists, deleted",
        "DELETE FROM session_vector_stores "
        "WHERE dd_type_id IS NOT NULL AND dd_type_id NOT IN (SELECT id FROM dd_types)",
    ),
    (
        "duplicate assignments deleted (the oldest kept)",
        "DELETE FROM session_vector_stores WHERE id IN ("
        + _ranked_out(
            "session_vector_stores",
            "session_id, dd_type_id, vector_store_id",
            "assigned_at ASC NULLS LAST, id ASC",
        )
        + ")",
    ),
    (
        "duplicate summaries deleted (the latest kept)",
        "DELETE FROM dd_summaries WHERE id IN ("
        + _ranked_out(
            "dd_summaries",
            "session_id, dd_type_id, section_id",
            "updated_at DESC NULLS LAST, id DESC",
        )
        + ")",
    ),
    # The code already reads NULL as false: is_(True) leaves these rows out.
    (
        "answers with is_current NULL set to false",
        "UPDATE dd_answers SET is_current = false WHERE is_current IS NULL",
    ),
    (
        "extra current answers set to not current (the latest kept)",
        "UPDATE dd_answers SET is_current = false WHERE id IN ("
        + _ranked_out("dd_answers", "execution_id, question_id", "id DESC", where="is_current")
        + ")",
    ),
    # A login of nobody: its token can no longer be refreshed by anyone.
    (
        "logins without a user deleted",
        "DELETE FROM user_sessions WHERE user_id IS NULL",
    ),
]


def _refuse_what_needs_a_decision(bind: sa.Connection) -> None:
    found = []
    for problem, query in NEEDS_A_DECISION:
        ids = [row[0] for row in bind.execute(sa.text(query))]
        if ids:
            shown = ", ".join(str(i) for i in ids[:20]) + (" ..." if len(ids) > 20 else "")
            found.append(f"- {len(ids)} {problem} (ids {shown})")
    if found:
        raise RuntimeError(
            "Migration 0002 stopped before any change: these rows call for a decision.\n"
            + "\n".join(found)
            + "\nscripts/audit_integrity.py lists them all."
        )


def _fix_data(bind: sa.Connection) -> None:
    for what, statement in FIXES:
        count = bind.execute(sa.text(statement)).rowcount
        if count:
            log.info("%s: %s", what, count)
    for table, column, _type, default in NOT_NULL:
        count = bind.execute(
            sa.text(f"UPDATE {table} SET {column} = {default or 'now()'} WHERE {column} IS NULL")
        ).rowcount
        if count:
            log.info("%s.%s NULL set to %s: %s", table, column, default or "now()", count)
    # Names to values: 'NEEDS_REVIEW' -> 'needs_review'.
    bind.execute(sa.text("UPDATE dd_answers SET status = lower(status)"))


def upgrade() -> None:
    """Upgrade schema."""
    # Offline, the SQL written (db/schema.sql) builds an empty database:
    # there is no data to check or to fix.
    online = not context.is_offline_mode()
    if online:
        _refuse_what_needs_a_decision(op.get_bind())

    # The old check wants the names: dropped before the data moves to values.
    op.drop_constraint(op.f("ck_dd_answers_answer_status"), "dd_answers", type_="check")
    if online:
        _fix_data(op.get_bind())

    for table, column, type_, default in NOT_NULL:
        if default is None:
            op.alter_column(table, column, existing_type=type_, nullable=False)
        else:
            op.alter_column(
                table,
                column,
                existing_type=type_,
                nullable=False,
                server_default=sa.text(default),
            )
    for table, column in REQUIRED_KEYS:
        op.alter_column(table, column, existing_type=sa.Integer(), nullable=False)

    op.create_check_constraint(
        op.f("ck_dd_answers_answer_status"), "dd_answers", f"status IN ({_in(ANSWER_STATUSES)})"
    )
    op.create_check_constraint(
        op.f("ck_dd_executions_execution_status"),
        "dd_executions",
        f"status IN ({_in(EXECUTION_STATUSES)})",
    )
    op.create_check_constraint(op.f("ck_users_role"), "users", f"role IN ({_in(ROLES)})")

    for name, table, columns in UNIQUE:
        op.create_unique_constraint(op.f(name), table, columns)
    for name, table, columns, condition in PARTIAL_UNIQUE:
        op.create_index(
            op.f(name), table, columns, unique=True, postgresql_where=sa.text(condition)
        )

    op.create_index(
        op.f("ix_session_vector_stores_dd_type_id"),
        "session_vector_stores",
        ["dd_type_id"],
        unique=False,
    )
    op.create_foreign_key(
        op.f("fk_session_vector_stores_dd_type_id_dd_types"),
        "session_vector_stores",
        "dd_types",
        ["dd_type_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        op.f("fk_session_vector_stores_dd_type_id_dd_types"),
        "session_vector_stores",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_session_vector_stores_dd_type_id"), table_name="session_vector_stores")

    for name, table, _columns, _condition in reversed(PARTIAL_UNIQUE):
        op.drop_index(op.f(name), table_name=table)
    for name, table, _columns in reversed(UNIQUE):
        op.drop_constraint(op.f(name), table, type_="unique")

    op.drop_constraint(op.f("ck_users_role"), "users", type_="check")
    op.drop_constraint(op.f("ck_dd_executions_execution_status"), "dd_executions", type_="check")
    op.drop_constraint(op.f("ck_dd_answers_answer_status"), "dd_answers", type_="check")

    for table, column in reversed(REQUIRED_KEYS):
        op.alter_column(table, column, existing_type=sa.Integer(), nullable=True)
    for table, column, type_, default in reversed(NOT_NULL):
        if default is None:
            op.alter_column(table, column, existing_type=type_, nullable=True)
        else:
            op.alter_column(
                table,
                column,
                existing_type=type_,
                nullable=True,
                server_default=None,
                existing_server_default=sa.text(default),
            )

    # Values back to names, as the old check wants them.
    if not context.is_offline_mode():
        op.get_bind().execute(sa.text("UPDATE dd_answers SET status = upper(status)"))
    op.create_check_constraint(
        op.f("ck_dd_answers_answer_status"),
        "dd_answers",
        f"status IN ({_in([status.upper() for status in ANSWER_STATUSES])})",
    )
