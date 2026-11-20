"""dead columns and copies: session status, dd_types_json, unused fields

- dd_sessions.status goes. It was set to 'created' and never moved again, so
  the deletion guard that read it never fired: a session could be deleted
  while it ran. A session's state is that of its runs (dd_executions). The
  index on (company_id, status) gives way to one on company_id, its foreign
  key.
- dd_sessions.dd_types_json, a JSON copy of the code and name of the DD types
  chosen, becomes the link table session_dd_types: a renamed DD type shows
  under its new name, and a DD type a session has chosen cannot be deleted.
  A code that matches no DD type is left out, and counted in the log.
- Unused: dd_answers.confidence_score (no longer filled) and its CHECK,
  dd_executions.validator_id (never written), users.is_verified (never set).

The data is moved online only: offline, the SQL written (db/schema.sql)
builds an empty database.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-20 14:40:00

"""

import json
import logging
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

log = logging.getLogger("alembic.0003")

# The names of dd_sessions.status as of 0001 (the column stored the names).
SESSION_STATUSES = ("CREATED", "DOCUMENTS_UPLOADED", "IN_PROGRESS", "COMPLETED", "FAILED", "PAUSED")


def _links_from_json(bind: sa.Connection) -> None:
    """session_dd_types from dd_types_json, in the order of the JSON."""
    ids = {
        code: dd_type_id
        for dd_type_id, code in bind.execute(sa.text("SELECT id, code FROM dd_types"))
    }
    links: list[dict[str, int]] = []
    unknown = unreadable = 0
    sessions = bind.execute(
        sa.text(
            "SELECT id, dd_types_json FROM dd_sessions WHERE dd_types_json IS NOT NULL ORDER BY id"
        )
    )
    for session_id, raw in sessions:
        try:
            codes = [entry["code"] for entry in json.loads(raw)]
        except (ValueError, TypeError, KeyError):
            unreadable += 1
            continue
        kept: list[int] = []
        for code in codes:
            if code not in ids:
                unknown += 1
            elif ids[code] not in kept:
                kept.append(ids[code])
        links += [
            {"session_id": session_id, "dd_type_id": dd_type_id, "position": position}
            for position, dd_type_id in enumerate(kept)
        ]
    if links:
        bind.execute(
            sa.text(
                "INSERT INTO session_dd_types (session_id, dd_type_id, position) "
                "VALUES (:session_id, :dd_type_id, :position)"
            ),
            links,
        )
    log.info(
        "dd_types_json: %s links written, %s unknown codes left out, %s unreadable values",
        len(links),
        unknown,
        unreadable,
    )


def _json_from_links(bind: sa.Connection) -> None:
    """dd_types_json back from session_dd_types, as the code wrote it."""
    rows = bind.execute(
        sa.text(
            "SELECT l.session_id, t.code, t.name FROM session_dd_types l "
            "JOIN dd_types t ON t.id = l.dd_type_id ORDER BY l.session_id, l.position"
        )
    )
    chosen: dict[int, list[dict[str, str]]] = {}
    for session_id, code, name in rows:
        chosen.setdefault(session_id, []).append({"code": code, "name": name})
    for session_id, dd_types in chosen.items():
        bind.execute(
            sa.text("UPDATE dd_sessions SET dd_types_json = :value WHERE id = :id"),
            {"value": json.dumps(dd_types), "id": session_id},
        )


def upgrade() -> None:
    """Upgrade schema."""
    online = not context.is_offline_mode()

    op.create_table(
        "session_dd_types",
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("dd_type_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["dd_type_id"],
            ["dd_types.id"],
            name=op.f("fk_session_dd_types_dd_type_id_dd_types"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["dd_sessions.id"],
            name=op.f("fk_session_dd_types_session_id_dd_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("session_id", "dd_type_id", name=op.f("pk_session_dd_types")),
    )
    op.create_index(
        op.f("ix_session_dd_types_dd_type_id"), "session_dd_types", ["dd_type_id"], unique=False
    )
    if online:
        _links_from_json(op.get_bind())
    op.drop_column("dd_sessions", "dd_types_json")

    op.drop_index("ix_dd_sessions_company_status", table_name="dd_sessions")
    op.drop_constraint(op.f("ck_dd_sessions_session_status"), "dd_sessions", type_="check")
    op.drop_column("dd_sessions", "status")
    op.create_index(op.f("ix_dd_sessions_company_id"), "dd_sessions", ["company_id"], unique=False)

    op.drop_constraint(op.f("ck_dd_answers_confidence_range"), "dd_answers", type_="check")
    op.drop_column("dd_answers", "confidence_score")

    op.drop_constraint(
        op.f("fk_dd_executions_validator_id_users"), "dd_executions", type_="foreignkey"
    )
    op.drop_column("dd_executions", "validator_id")

    op.drop_column("users", "is_verified")


def downgrade() -> None:
    """Downgrade schema."""
    online = not context.is_offline_mode()

    op.add_column(
        "users",
        sa.Column("is_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )

    op.add_column("dd_executions", sa.Column("validator_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        op.f("fk_dd_executions_validator_id_users"),
        "dd_executions",
        "users",
        ["validator_id"],
        ["id"],
    )

    op.add_column("dd_answers", sa.Column("confidence_score", sa.Float(), nullable=True))
    op.create_check_constraint(
        op.f("ck_dd_answers_confidence_range"),
        "dd_answers",
        "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
    )

    # Every session back to 'CREATED': the value the column always held.
    op.drop_index(op.f("ix_dd_sessions_company_id"), table_name="dd_sessions")
    op.add_column(
        "dd_sessions",
        sa.Column("status", sa.String(50), server_default=sa.text("'CREATED'"), nullable=True),
    )
    op.alter_column("dd_sessions", "status", existing_type=sa.String(50), server_default=None)
    op.create_check_constraint(
        op.f("ck_dd_sessions_session_status"),
        "dd_sessions",
        "status IN ({})".format(", ".join(f"'{status}'" for status in SESSION_STATUSES)),
    )
    op.create_index(
        "ix_dd_sessions_company_status", "dd_sessions", ["company_id", "status"], unique=False
    )

    op.add_column("dd_sessions", sa.Column("dd_types_json", sa.Text(), nullable=True))
    if online:
        _json_from_links(op.get_bind())
    op.drop_index(op.f("ix_session_dd_types_dd_type_id"), table_name="session_dd_types")
    op.drop_table("session_dd_types")
