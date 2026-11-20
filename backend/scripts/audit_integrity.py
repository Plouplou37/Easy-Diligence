"""Read-only audit of the data, to run before migration 0002.

Migration 0002 lays the rules the code took for granted: one execution per
session and DD type, at most one current answer per question, one summary and
one assignment per scope, unique codes, no NULL where a value is required, and
a CHECK on every status. A row that already breaks one of them would make the
migration fail. This lists them beforehand, with their ids, and says what the
migration does with each: it fixes some (as described), and stops on the others,
which call for a decision.

From backend/, against the database of backend/.env (DATABASE_URL or POSTGRES_*):

    uv run python scripts/audit_integrity.py          # the first 20 ids of each
    uv run python scripts/audit_integrity.py --all    # every id

Nothing is written: the transaction is read-only on PostgreSQL, and rolled back
at the end. The exit code is 1 when something calls for a decision.
"""

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any, get_args

from sqlalchemy import Connection, Table, create_engine, inspect, text

from app.core.database_settings import DatabaseSettings, load_settings
from app.models import ExecutionStatus
from app.models.base import SQLModel
from app.models.user import Role

DECIDE = "migration 0002 stops: your decision first"
UNTOUCHED = "nothing (migration 0003 leaves these codes out)"


@dataclass
class Finding:
    problem: str
    action: str  # what migration 0002 does with these rows
    ids: list[Any]

    @property
    def blocking(self) -> bool:
        return self.action == DECIDE

    @property
    def tag(self) -> str:
        if self.blocking:
            return "[DECIDE]"
        return "[info]  " if self.action == UNTOUCHED else "[fixed] "


def _ids(connection: Connection, query: str) -> list[Any]:
    return [row[0] for row in connection.execute(text(query))]


def _duplicates(table: str, keys: str, where: str = "1 = 1") -> str:
    """The rows sharing their `keys` with another row. NULL counts as a value,
    as PARTITION BY does."""
    return (
        f"SELECT id FROM (SELECT id, count(*) OVER (PARTITION BY {keys}) AS n "
        f"FROM {table} WHERE {where}) AS counted WHERE n > 1 ORDER BY id"
    )


def _in(values: Any) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _rule_checks(connection: Connection) -> list[Finding]:
    checks = [
        (
            "executions sharing their (session, DD type)",
            DECIDE,
            _duplicates("dd_executions", "session_id, dd_type_id"),
        ),
        (
            "current answers sharing their (execution, question)",
            "the latest (highest id) stays current, the others are set to not current",
            _duplicates("dd_answers", "execution_id, question_id", where="is_current"),
        ),
        (
            "answers without an execution or a question",
            DECIDE,
            "SELECT id FROM dd_answers WHERE execution_id IS NULL OR question_id IS NULL "
            "ORDER BY id",
        ),
        (
            "summaries sharing their (session, DD type, section), synthesis included",
            "the latest (updated_at, then id) is kept, the others deleted",
            _duplicates("dd_summaries", "session_id, dd_type_id, section_id"),
        ),
        (
            "assignments sharing their (session, DD type or whole session, store)",
            "the oldest is kept, the others deleted",
            _duplicates("session_vector_stores", "session_id, dd_type_id, vector_store_id"),
        ),
        (
            "assignments to a DD type that no longer exists",
            "deleted",
            "SELECT id FROM session_vector_stores WHERE dd_type_id IS NOT NULL "
            "AND dd_type_id NOT IN (SELECT id FROM dd_types) ORDER BY id",
        ),
        (
            "sections sharing their code within a DD type",
            DECIDE,
            _duplicates("dd_sections", "dd_type_id, section_code"),
        ),
        (
            "questions sharing their code within a section",
            DECIDE,
            _duplicates("dd_questions", "section_id, question_code"),
        ),
        (
            "executions with an unknown status",
            DECIDE,
            "SELECT id FROM dd_executions "
            f"WHERE status NOT IN ({_in(status.value for status in ExecutionStatus)}) ORDER BY id",
        ),
        (
            "users with an unknown role",
            DECIDE,
            f"SELECT id FROM users WHERE role NOT IN ({_in(get_args(Role))}) ORDER BY id",
        ),
    ]
    return [Finding(problem, action, _ids(connection, query)) for problem, action, query in checks]


# NULL in these columns is not set to a default, unlike the other NOT NULL columns.
_NULL_ACTIONS = {
    ("dd_answers", "is_current"): "set to false (the code already reads NULL as false)",
    ("dd_answers", "execution_id"): None,  # listed above, with the answers without a question
    ("dd_answers", "question_id"): None,
    ("user_sessions", "user_id"): "deleted (a login of nobody)",
}


def _default_of(table: Table, column: str) -> str:
    server_default = table.c[column].server_default
    arg = getattr(server_default, "arg", None)
    if arg is None:
        return "?"
    return arg if isinstance(arg, str) else str(arg)


def _columns(connection: Connection, table: str) -> set[str]:
    """The columns the table has in this database; none if it has no such
    table. The script runs on databases of any revision."""
    inspector = inspect(connection)
    if not inspector.has_table(table):
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def _null_checks(connection: Connection) -> list[Finding]:
    """NULL in every column the models declare NOT NULL. Those already NOT
    NULL in the database find nothing; tables and columns the database does
    not have yet are left out."""
    findings = []
    for table in SQLModel.metadata.sorted_tables:
        present = _columns(connection, table.name)
        key = next(iter(table.primary_key.columns)).name
        for column in table.columns:
            if column.nullable or column.primary_key or column.name not in present:
                continue
            action = _NULL_ACTIONS.get(
                (table.name, column.name),
                f"set to the default, {_default_of(table, column.name)}",
            )
            if action is None:
                continue
            ids = _ids(
                connection,
                f"SELECT {key} FROM {table.name} WHERE {column.name} IS NULL ORDER BY {key}",
            )
            findings.append(Finding(f"{table.name}.{column.name} NULL", action, ids))
    return findings


def _unknown_dd_type_codes(connection: Connection) -> Finding:
    """Sessions whose dd_types_json names a DD type that does not exist (or is
    not readable JSON). Not touched by 0002: listed for 0003, which replaces
    this column with a table and leaves these codes out. Nothing to list once
    0003 has run."""
    codes = {row[0] for row in connection.execute(text("SELECT code FROM dd_types"))}
    ids: list[Any] = []
    if "dd_types_json" not in _columns(connection, "dd_sessions"):
        return Finding("sessions naming an unknown DD type in dd_types_json", UNTOUCHED, ids)
    rows = connection.execute(
        text(
            "SELECT id, dd_types_json FROM dd_sessions WHERE dd_types_json IS NOT NULL ORDER BY id"
        )
    )
    for session_id, raw in rows:
        try:
            chosen = {entry["code"] for entry in json.loads(raw)}
        except (ValueError, TypeError, KeyError):
            ids.append(session_id)
            continue
        if chosen - codes:
            ids.append(session_id)
    return Finding(
        "sessions naming an unknown DD type in dd_types_json",
        UNTOUCHED,
        ids,
    )


def audit(connection: Connection) -> list[Finding]:
    """Every check, found or not, in a stable order."""
    return [
        *_rule_checks(connection),
        *_null_checks(connection),
        _unknown_dd_type_codes(connection),
    ]


def report(findings: list[Finding], show_all: bool) -> str:
    lines = []
    for finding in findings:
        if not finding.ids:
            continue
        ids = finding.ids if show_all else finding.ids[:20]
        more = "" if len(ids) == len(finding.ids) else f" ... ({len(finding.ids)} in all)"
        lines += [
            f"{finding.tag} {len(finding.ids)} {finding.problem}",
            f"          0002: {finding.action}",
            f"          ids: {', '.join(str(i) for i in ids)}{more}",
        ]
    found = sum(1 for finding in findings if finding.ids)
    lines.append(f"{found} finding(s) out of {len(findings)} checks.")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--all", action="store_true", help="list every id, not the first 20")
    args = parser.parse_args()

    engine = create_engine(load_settings(DatabaseSettings).sqlalchemy_database_url)
    with engine.connect() as connection:
        if connection.dialect.name == "postgresql":
            connection.execute(text("SET TRANSACTION READ ONLY"))
        findings = audit(connection)
        connection.rollback()
    print(report(findings, args.all))
    return 1 if any(finding.blocking and finding.ids for finding in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
