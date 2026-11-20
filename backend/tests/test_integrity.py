"""The rules the database holds (migration 0002), and the code that turns a
violation into a readable answer rather than a 500.

Races are played by making the first read miss, as when two requests read
before either writes: the database then has the last word.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

import app.engine.summarizer as summarizer
import app.services.processing as processing
import app.services.questions as questions_service
import app.services.vector_stores as vector_stores_service
from app.core.exceptions import InvalidRequestError
from app.models.answer import AnswerStatus, DDAnswer
from app.models.execution import DDExecution, ExecutionStatus
from app.models.questions import DDQuestion
from app.models.summary import DDSummary
from app.models.vector_store import SessionVectorStore, VectorStore


def _miss_once(monkeypatch, module, name):
    """The first call of module.name finds nothing; the next ones are real."""
    real = getattr(module, name)
    calls = []

    def first_misses(*args, **kwargs):
        calls.append(args)
        return None if len(calls) == 1 else real(*args, **kwargs)

    monkeypatch.setattr(module, name, first_misses)
    return calls


@pytest.fixture
def run(db, analyst, make_dd_type, make_dd_session):
    """A session and a DD type with no run yet."""
    return make_dd_session(analyst), make_dd_type(questions=2)


def _execution(db):
    db.expire_all()
    return db.query(DDExecution).one()


def _set_status(db, status, *, idle_for=timedelta(0)):
    execution = _execution(db)
    execution.status = status
    execution.updated_at = datetime.now(UTC) - idle_for
    db.commit()


def _answer(db, execution, question, **fields):
    answer = DDAnswer(
        session_id=execution.session_id,
        execution_id=execution.id,
        question_id=question.id,
        section_code="A",
        question_code=question.question_code,
        **fields,
    )
    db.add(answer)
    db.commit()
    return answer


# --- One execution per (session, DD type), and its status ------------------------


def test_two_simultaneous_starts_make_one_execution(db, run, monkeypatch):
    session, dd_type = run
    processing.start(db, session, dd_type)

    # The second start read before the first one wrote: it finds no execution.
    reads = _miss_once(monkeypatch, processing, "find_execution")
    with pytest.raises(InvalidRequestError, match="already in progress"):
        processing.start(db, session, dd_type)

    assert len(reads) == 2  # refused by the database, then read again
    assert db.query(DDExecution).count() == 1
    assert _execution(db).status == ExecutionStatus.IN_PROGRESS


def test_the_database_refuses_a_second_execution(db, run):
    session, dd_type = run
    db.add(DDExecution(session_id=session.id, dd_type_id=dd_type.id))
    db.commit()
    db.add(DDExecution(session_id=session.id, dd_type_id=dd_type.id))
    with pytest.raises(IntegrityError):
        db.commit()


def test_two_clicks_on_resume_launch_one_run(db, session_factory, run):
    session, dd_type = run
    processing.start(db, session, dd_type)
    _set_status(db, ExecutionStatus.PAUSED)

    # Both requests read the paused run before either changes it.
    first, second = session_factory(), session_factory()
    assert processing.get_execution(first, session.id, dd_type.id).status == "paused"
    assert processing.get_execution(second, session.id, dd_type.id).status == "paused"

    processing.resume(first, session, dd_type)
    with pytest.raises(InvalidRequestError, match="already in progress"):
        processing.resume(second, session, dd_type)
    assert _execution(db).status == ExecutionStatus.IN_PROGRESS


def test_two_clicks_on_start_launch_one_run(db, session_factory, run):
    session, dd_type = run
    processing.start(db, session, dd_type)
    _set_status(db, ExecutionStatus.FAILED)

    first, second = session_factory(), session_factory()
    processing.get_execution(second, session.id, dd_type.id)  # read before the first start
    processing.start(first, session, dd_type)
    with pytest.raises(InvalidRequestError, match="already in progress"):
        processing.start(second, session, dd_type)


def test_pause_only_stops_a_running_run(db, run):
    session, dd_type = run
    processing.start(db, session, dd_type)
    assert processing.pause(db, session, dd_type).status == ExecutionStatus.PAUSED
    with pytest.raises(InvalidRequestError, match="Cannot pause execution with status paused"):
        processing.pause(db, session, dd_type)


def test_a_stuck_run_is_taken_over_once(db, run):
    session, dd_type = run
    processing.start(db, session, dd_type)
    _set_status(db, ExecutionStatus.IN_PROGRESS, idle_for=timedelta(hours=1))

    with pytest.raises(InvalidRequestError, match="looks stuck"):
        processing.start(db, session, dd_type)
    processing.resume(db, session, dd_type)
    # The takeover counts as activity: a second resume finds the run going on.
    with pytest.raises(InvalidRequestError, match="already in progress"):
        processing.resume(db, session, dd_type)


def test_a_long_run_that_still_answers_is_not_stuck(db, run):
    """The engine leaves the execution row alone while it answers: its answers
    are what shows that it is alive."""
    session, dd_type = run
    processing.start(db, session, dd_type)
    _set_status(db, ExecutionStatus.IN_PROGRESS, idle_for=timedelta(hours=1))
    _answer(db, _execution(db), db.query(DDQuestion).first())

    with pytest.raises(InvalidRequestError, match="already in progress"):
        processing.resume(db, session, dd_type)


def test_execution_statuses_are_checked_and_stored_lowercase(db, run):
    session, dd_type = run
    processing.start(db, session, dd_type)
    assert db.execute(text("SELECT status FROM dd_executions")).scalar() == "in_progress"
    with pytest.raises(IntegrityError):
        db.execute(text("UPDATE dd_executions SET status = 'IN_PROGRESS'"))


# --- At most one current answer per question ---------------------------------------


def test_a_second_current_answer_is_refused(db, run):
    session, dd_type = run
    processing.start(db, session, dd_type)
    execution, question = _execution(db), db.query(DDQuestion).first()
    _answer(db, execution, question)

    _answer(db, execution, question, is_current=False)  # an older version: fine
    with pytest.raises(IntegrityError):
        _answer(db, execution, question)


def test_answer_statuses_are_stored_by_value(db, run):
    session, dd_type = run
    processing.start(db, session, dd_type)
    _answer(db, _execution(db), db.query(DDQuestion).first(), status=AnswerStatus.COMPLETED)
    assert db.execute(text("SELECT status FROM dd_answers")).scalar() == "completed"
    with pytest.raises(IntegrityError):
        db.execute(text("UPDATE dd_answers SET status = 'COMPLETED'"))


# --- Defaults set by the database --------------------------------------------------


def test_a_row_inserted_in_sql_gets_the_defaults(db):
    db.execute(
        text(
            "INSERT INTO users (email, username, password_hash) "
            "VALUES ('sql@example.com', 'sql', 'x')"
        )
    )
    row = db.execute(
        text("SELECT role, is_active, is_verified, created_at, updated_at FROM users")
    ).one()
    assert (row.role, row.is_active, row.is_verified) == ("analyst", 1, 0)
    assert row.created_at is not None
    assert row.updated_at is None  # NULL until the first change


def test_an_unknown_role_is_refused(db, analyst):
    with pytest.raises(IntegrityError):
        db.execute(text("UPDATE users SET role = 'owner'"))


def test_a_null_does_not_empty_a_required_field_of_a_dd_type(
    client, analyst, make_dd_type, auth_headers
):
    dd_type = make_dd_type(analyst)
    response = client.put(
        f"/api/dd-types/{dd_type.code}",
        json={"is_active": None, "order_index": None, "description": None},
        headers=auth_headers(analyst),
    )
    assert response.status_code == 200
    assert (response.json()["is_active"], response.json()["order_index"]) == (True, 0)


# --- Codes ---------------------------------------------------------------------------


def test_a_section_code_already_taken_is_a_conflict(client, analyst, make_dd_type, auth_headers):
    dd_type = make_dd_type(analyst, sections=2)
    second = next(s for s in dd_type.sections if s.section_code == "B")
    response = client.put(
        f"/api/questions/sections/{second.id}",
        json={"section_code": "A"},
        headers=auth_headers(analyst),
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Section code already exists in this DD type"


def test_a_section_added_at_the_same_time_is_a_conflict(
    client, analyst, make_dd_type, auth_headers, monkeypatch
):
    dd_type = make_dd_type(analyst)
    # As if another request had taken "B" between the read and the write.
    monkeypatch.setattr(questions_service, "next_section_code", lambda existing: "A")
    response = client.post(
        f"/api/questions/dd-types/{dd_type.code}/sections",
        json={"title": "Fees"},
        headers=auth_headers(analyst),
    )
    assert response.status_code == 409
    assert [s.section_code for s in dd_type.sections] == ["A"]


def test_the_database_refuses_a_duplicate_question_code(db, make_dd_type):
    section = make_dd_type().sections[0]
    db.add(DDQuestion(section_id=section.id, question_code="A.01", question_text="Again?"))
    with pytest.raises(IntegrityError):
        db.commit()


# --- One assignment per scope ---------------------------------------------------------


@pytest.fixture
def store(db, analyst):
    db.add(VectorStore(id="vs_1", name="Fund documents", created_by=analyst.id))
    db.commit()
    return "vs_1"


@pytest.mark.parametrize("for_one_dd_type", [False, True])
def test_a_double_assignment_leaves_one_row(
    db,
    client,
    analyst,
    store,
    make_dd_session,
    make_dd_type,
    auth_headers,
    fake_vector_stores,
    monkeypatch,
    for_one_dd_type,
):
    session = make_dd_session(analyst)
    body = {"dd_type_id": make_dd_type().id} if for_one_dd_type else None
    url = f"/api/vector-stores/{store}/assign-session/{session.id}"
    headers = auth_headers(analyst)

    assert client.put(url, json=body, headers=headers).status_code == 200
    # The second request read before the first one wrote.
    reads = _miss_once(monkeypatch, vector_stores_service, "_find_assignment")
    second = client.put(url, json=body, headers=headers)

    assert len(reads) == 2  # refused by the database, then read again
    assert second.status_code == 200
    assert second.json()["message"] == "Vector store already assigned to session"
    assert db.query(SessionVectorStore).count() == 1


def test_deleting_a_dd_type_deletes_its_assignments(
    db, analyst, store, make_dd_session, make_dd_type
):
    session, dd_type = make_dd_session(analyst), make_dd_type()
    db.add(
        SessionVectorStore(
            session_id=session.id,
            dd_type_id=dd_type.id,
            vector_store_id=store,
            assigned_by=analyst.id,
        )
    )
    db.commit()
    db.execute(text("DELETE FROM dd_questions"))
    db.execute(text("DELETE FROM dd_sections"))
    db.execute(text("DELETE FROM dd_types"))
    db.commit()
    assert db.query(SessionVectorStore).count() == 0


# --- One summary per scope -----------------------------------------------------------


@pytest.mark.parametrize("for_a_section", [False, True])
def test_a_summary_written_twice_leaves_one_row(
    db, analyst, make_dd_type, make_dd_session, monkeypatch, for_a_section
):
    session, dd_type = make_dd_session(analyst), make_dd_type()
    section_id = dd_type.sections[0].id if for_a_section else None  # None: the synthesis
    summarizer._upsert_summary(db, session.id, dd_type.id, section_id, "First")
    db.commit()

    # The second generation read before the first one wrote.
    reads = _miss_once(monkeypatch, summarizer, "_find_summary")
    summarizer._upsert_summary(db, session.id, dd_type.id, section_id, "Second")
    db.commit()

    assert len(reads) == 2  # refused by the database, then read again
    db.expire_all()
    assert [s.summary_text for s in db.query(DDSummary).all()] == ["Second"]
