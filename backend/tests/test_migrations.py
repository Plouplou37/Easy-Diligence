"""The data moves of the migrations, played on the test database.

The migrations themselves run on PostgreSQL only (the CI plays them, up and
down). What they do to the data is plain SQL, so it runs on the test database
too, and the rules can be checked here: order kept, unknown codes left out.
"""

import importlib.util
import json
from pathlib import Path

import pytest
from sqlalchemy import text

from app.models.session import SessionDDType

VERSIONS = Path(__file__).resolve().parents[1] / "alembic" / "versions"


@pytest.fixture(scope="module")
def m0003():
    spec = importlib.util.spec_from_file_location("m0003", VERSIONS / "0003_dead_columns.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _set_json(db, session, value):
    db.execute(
        text("UPDATE dd_sessions SET dd_types_json = :value WHERE id = :id"),
        {"value": value, "id": session.id},
    )
    db.commit()


def test_0003_turns_dd_types_json_into_links_and_back(
    dd_types_json, engine, db, analyst, make_dd_type, make_dd_session, m0003
):
    first, second = make_dd_type(), make_dd_type()
    chosen, unreadable = make_dd_session(analyst), make_dd_session(analyst)
    # The order of the JSON, an unknown code, a code twice.
    codes = [second.code, "GONE", first.code, second.code]
    _set_json(db, chosen, json.dumps([{"code": code, "name": code} for code in codes]))
    _set_json(db, unreadable, "not json")

    with engine.begin() as connection:
        m0003._links_from_json(connection)
    links = db.query(SessionDDType).order_by(SessionDDType.position).all()
    assert [(link.session_id, link.dd_type_id, link.position) for link in links] == [
        (chosen.id, second.id, 0),
        (chosen.id, first.id, 1),
    ]

    # And back, with the current names.
    _set_json(db, chosen, None)
    with engine.begin() as connection:
        m0003._json_from_links(connection)
    value = db.execute(
        text("SELECT dd_types_json FROM dd_sessions WHERE id = :id"), {"id": chosen.id}
    ).scalar()
    assert json.loads(value) == [
        {"code": second.code, "name": second.name},
        {"code": first.code, "name": first.name},
    ]
