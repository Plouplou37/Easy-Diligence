"""What only PostgreSQL can show: a schema built by the migrations, unique
indexes that really are partial, the CHECK constraints, JSONB and timestamps
with a time zone.

Marked `postgres`: skipped on SQLite. The CI runs them on its throwaway
PostgreSQL (TEST_POSTGRES_URL, tests/conftest.py).
"""

from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.models.execution import DDExecution
from app.models.questions import DDQuestion

MIGRATIONS = Path(__file__).resolve().parents[1] / "alembic"

pytestmark = pytest.mark.postgres


@pytest.fixture
def execution(db, analyst, make_dd_type, make_dd_session):
    dd_type, session = make_dd_type(), make_dd_session(analyst)
    execution = DDExecution(session_id=session.id, dd_type_id=dd_type.id)
    db.add(execution)
    db.commit()
    return execution


def _insert_answer(db, execution, question, current=True):
    db.execute(
        text(
            "INSERT INTO dd_answers (session_id, execution_id, question_id, section_code, "
            "question_code, is_current) VALUES (:s, :e, :q, 'A', :code, :current)"
        ),
        {
            "s": execution.session_id,
            "e": execution.id,
            "q": question.id,
            "code": question.question_code,
            "current": current,
        },
    )


def test_the_schema_comes_from_the_migrations(db):
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS))
    head = ScriptDirectory.from_config(config).get_current_head()
    assert db.execute(text("SELECT version_num FROM alembic_version")).scalar() == head


def test_the_unique_indexes_are_partial(db):
    definitions = dict(
        db.execute(
            text("SELECT indexname, indexdef FROM pg_indexes WHERE indexname LIKE 'ix_%_one_%'")
        ).all()
    )
    assert definitions["ix_dd_answers_one_current"].endswith("WHERE is_current")
    assert definitions["ix_dd_summaries_one_synthesis"].endswith("WHERE (section_id IS NULL)")
    assert definitions["ix_session_vector_stores_one_session_wide"].endswith(
        "WHERE (dd_type_id IS NULL)"
    )


def test_the_partial_index_refuses_a_second_current_answer(db, execution):
    question = db.query(DDQuestion).first()
    _insert_answer(db, execution, question)
    _insert_answer(db, execution, question, current=False)  # history: fine
    with pytest.raises(IntegrityError):
        _insert_answer(db, execution, question)


def test_a_second_synthesis_is_refused(db, execution):
    insert = text(
        "INSERT INTO dd_summaries (session_id, dd_type_id, summary_text) VALUES (:s, :t, 'x')"
    )
    values = {"s": execution.session_id, "t": execution.dd_type_id}
    db.execute(insert, values)
    with pytest.raises(IntegrityError):
        db.execute(insert, values)


@pytest.mark.parametrize(
    ("table", "column", "value"),
    [
        ("dd_executions", "status", "IN_PROGRESS"),
        ("dd_answers", "status", "NEEDS_REVIEW"),
        ("users", "role", "owner"),
    ],
)
def test_check_constraints_refuse_an_unknown_value(db, execution, table, column, value):
    _insert_answer(db, execution, db.query(DDQuestion).first())
    with pytest.raises(IntegrityError):
        db.execute(text(f"UPDATE {table} SET {column} = :value"), {"value": value})


def test_json_is_jsonb_and_dates_carry_their_time_zone(db, execution):
    types = dict(
        db.execute(
            text(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name = 'dd_answers' AND column_name IN ('sources', 'created_at')"
            )
        ).all()
    )
    assert types == {"sources": "jsonb", "created_at": "timestamp with time zone"}

    db.refresh(execution)
    assert execution.created_at.tzinfo is not None
