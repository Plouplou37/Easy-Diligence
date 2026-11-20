"""scripts/audit_integrity.py: its queries run, and find what they look for.

The test database already holds the rules of migration 0002, so most findings
cannot be planted here: what is checked is that every query runs and that a
sound database gives nothing to report.
"""

import importlib.util
import json
from pathlib import Path

import pytest
from sqlalchemy import text

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_integrity.py"


@pytest.fixture(scope="module")
def audit_script():
    spec = importlib.util.spec_from_file_location("audit_integrity", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _findings(engine, audit_script):
    with engine.connect() as connection:
        return audit_script.audit(connection)


def test_a_sound_database_has_nothing_to_report(
    engine, db, analyst, make_dd_type, make_dd_session, audit_script
):
    make_dd_type()
    make_dd_session(analyst)
    findings = _findings(engine, audit_script)

    assert [f.problem for f in findings if f.ids] == []
    assert "0 finding(s)" in audit_script.report(findings, show_all=False)


# dd_types_json first: on PostgreSQL, ALTER TABLE waits for the locks of the
# sessions opened before it.
def test_an_unknown_dd_type_code_is_listed(
    dd_types_json, engine, db, analyst, make_dd_type, make_dd_session, audit_script
):
    known = make_dd_type()
    session = make_dd_session(analyst)
    chosen = [{"code": known.code, "name": "Known"}, {"code": "GONE", "name": "Deleted"}]
    db.execute(
        text("UPDATE dd_sessions SET dd_types_json = :chosen WHERE id = :id"),
        {"chosen": json.dumps(chosen), "id": session.id},
    )
    db.commit()

    found = [f for f in _findings(engine, audit_script) if f.ids]
    assert [(f.problem, f.ids, f.blocking) for f in found] == [
        ("sessions naming an unknown DD type in dd_types_json", [session.id], False)
    ]
