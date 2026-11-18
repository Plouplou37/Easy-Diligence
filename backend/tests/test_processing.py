"""The answering engine, driven through the API: start, pause, resume.

OpenAI is replaced by FakeEngine. The background task runs inside the request
(the test client waits for it), on the test database.
"""

import pytest

import app.engine.processor as processor_module
from app.models.answer import AnswerStatus, DDAnswer, ErrorType
from app.models.execution import DDExecution, ExecutionStatus
from app.models.message import DDMessage
from app.models.response import DDResponse


class FakeEngine:
    """Stands in for OpenAIProcessor.process_question. Answers every question,
    except the call numbers listed in fail_on; on_call runs before answering."""

    def __init__(self):
        self.calls = []
        self.fail_on = set()
        self.on_call = None

    def process_question(
        self, question_text, vector_store_ids, previous_response_id, company_info, **_
    ):
        number = len(self.calls) + 1
        self.calls.append({"question": question_text, "previous": previous_response_id})
        if self.on_call:
            self.on_call(number)
        if number in self.fail_on:
            raise ValueError("invalid request")  # a validation error: not retried
        return {
            "response_id": f"resp_{number}",
            "previous_response_id": previous_response_id,
            "full_response": {"id": f"resp_{number}"},
            "messages": [{"id": f"msg_{number}", "role": "assistant", "content": "An answer"}],
            "sources": {"files": [], "web": [], "total_count": 0},
            "answer": f"Answer {number}",
            "tokens_used": 10,
        }


@pytest.fixture
def engine_client(monkeypatch):
    fake = FakeEngine()
    monkeypatch.setattr(processor_module, "OpenAIProcessor", lambda: fake)
    return fake


@pytest.fixture
def run(client, analyst, make_dd_type, make_dd_session, auth_headers):
    """A session of the analyst on a 3-question questionnaire, and a helper to
    call the processing endpoints on it."""
    dd_type = make_dd_type(questions=3)
    session = make_dd_session(analyst)
    headers = auth_headers(analyst)

    def _call(action, method="post"):
        url = f"/api/processing/session/{session.id}/dd/{dd_type.code}/{action}"
        return client.request(method, url, headers=headers)

    _call.session, _call.dd_type = session, dd_type
    return _call


def _execution(db):
    db.expire_all()
    return db.query(DDExecution).one()


def _pause(session_factory):
    """What the pause button does, from another session while the run goes on."""
    other = session_factory()
    other.query(DDExecution).one().status = ExecutionStatus.PAUSED
    other.commit()
    other.close()


def _answers(db, **filters):
    db.expire_all()
    return db.query(DDAnswer).filter_by(**filters).order_by(DDAnswer.id).all()


def test_start_answers_every_question_in_one_chained_conversation(db, run, engine_client):
    assert run("start").status_code == 200

    assert _execution(db).status == ExecutionStatus.GENERATED
    answers = _answers(db)
    assert [a.status for a in answers] == [AnswerStatus.COMPLETED] * 3
    assert [a.answer_text for a in answers] == ["Answer 1", "Answer 2", "Answer 3"]
    # Each question continues the conversation of the previous one.
    assert [c["previous"] for c in engine_client.calls] == [None, "resp_1", "resp_2"]
    assert db.query(DDResponse).count() == 3
    assert db.query(DDMessage).count() == 3


def test_a_generated_run_cannot_be_restarted(run, engine_client):
    run("start")
    response = run("start")
    assert response.status_code == 400
    assert len(engine_client.calls) == 3


def test_progress(run, engine_client):
    assert run("progress", "get").status_code == 404
    run("start")
    progress = run("progress", "get").json()
    assert progress["status"] == ExecutionStatus.GENERATED


def test_only_a_running_execution_can_be_paused(db, run, engine_client):
    run("start")
    assert run("pause").status_code == 400  # already generated

    execution = _execution(db)
    execution.status = ExecutionStatus.IN_PROGRESS
    db.commit()
    assert run("pause").status_code == 200
    assert _execution(db).status == ExecutionStatus.PAUSED


def test_pause_stops_the_run_between_questions(db, session_factory, run, engine_client):
    engine_client.on_call = lambda n: _pause(session_factory) if n == 1 else None
    run("start")

    assert _execution(db).status == ExecutionStatus.PAUSED
    assert len(_answers(db)) == 1
    assert len(engine_client.calls) == 1


def test_resume_skips_answered_questions_and_keeps_the_conversation(
    db, session_factory, run, engine_client
):
    engine_client.on_call = lambda n: _pause(session_factory) if n == 1 else None
    run("start")
    conversation = _execution(db).conversation_id
    engine_client.on_call = None

    assert run("resume").status_code == 200

    execution = _execution(db)
    assert execution.status == ExecutionStatus.GENERATED
    assert execution.conversation_id == conversation
    assert len(engine_client.calls) == 3  # 1 before the pause, 2 after
    assert engine_client.calls[1]["previous"] == "resp_1"
    assert len(_answers(db, status=AnswerStatus.COMPLETED)) == 3


def test_a_failed_question_fails_the_run_and_resume_retries_only_it(db, run, engine_client):
    engine_client.fail_on = {2}
    run("start")

    assert _execution(db).status == ExecutionStatus.FAILED
    failed = _answers(db, status=AnswerStatus.FAILED)
    assert len(failed) == 1
    assert failed[0].error_type == ErrorType.VALIDATION_ERROR
    assert len(_answers(db, status=AnswerStatus.COMPLETED)) == 2

    engine_client.fail_on = set()
    run("resume")

    assert _execution(db).status == ExecutionStatus.GENERATED
    assert len(engine_client.calls) == 4  # 3 on start, only the failed one on resume
    current = _answers(db, is_current=True)
    assert [a.status for a in current] == [AnswerStatus.COMPLETED] * 3


def test_processing_someone_elses_session_is_refused(
    client, make_user, make_dd_type, make_dd_session, auth_headers, engine_client
):
    dd_type = make_dd_type()
    session = make_dd_session(make_user())
    response = client.post(
        f"/api/processing/session/{session.id}/dd/{dd_type.code}/start",
        headers=auth_headers(make_user()),
    )
    assert response.status_code == 403
    assert engine_client.calls == []
