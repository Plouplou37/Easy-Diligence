"""The answering engine, driven through the API: start, pause, resume.

OpenAI is replaced by FakeEngine. The background task runs inside the request
(the test client waits for it), on the test database.
"""

import httpx
import openai
import pytest

import app.engine.processor as processor_module
from app.models.answer import AnswerStatus, DDAnswer, ErrorType
from app.models.execution import DDExecution, ExecutionStatus
from app.models.message import DDMessage
from app.models.response import DDResponse


def openai_error(cls, status, message="invalid request", headers=None, **body):
    """An error of the OpenAI SDK, as the client raises it."""
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx.Response(status, request=request, headers=headers)
    return cls(message, response=response, body=body or None)


class FakeEngine:
    """Stands in for OpenAIProcessor.process_question. Answers every question,
    except the call numbers listed in fail_on, or given an error to raise in
    `errors`; on_call runs before answering."""

    def __init__(self):
        self.calls = []
        self.fail_on = set()
        self.errors = {}
        self.on_call = None

    def process_question(
        self, question_text, vector_store_ids, previous_response_id, company_info, **_
    ):
        number = len(self.calls) + 1
        self.calls.append({"question": question_text, "previous": previous_response_id})
        if self.on_call:
            self.on_call(number)
        if number in self.fail_on:
            # A validation error: not retried, and local to the question.
            raise openai_error(openai.BadRequestError, 400)
        if number in self.errors:
            raise self.errors[number]
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


def test_a_crash_of_the_run_marks_it_failed(db, run, engine_client, monkeypatch):
    """The background run must not stay "in progress" forever."""

    def crash(self, *args):
        raise RuntimeError("the engine fell over")

    monkeypatch.setattr(processor_module.DDProcessor, "start_processing", crash)
    assert run("start").status_code == 200
    assert _execution(db).status == ExecutionStatus.FAILED


def test_a_private_dd_type_of_someone_else_cannot_be_run(
    client, analyst, make_user, make_dd_type, make_dd_session, auth_headers, engine_client
):
    private = make_dd_type(make_user())
    session = make_dd_session(analyst)
    response = client.post(
        f"/api/processing/session/{session.id}/dd/{private.code}/start",
        headers=auth_headers(analyst),
    )
    assert response.status_code == 404
    assert engine_client.calls == []


# --- The engine's own rules ----------------------------------------------------


def test_a_failed_write_leaves_the_question_as_it_was(db, run, engine_client, monkeypatch):
    """One transaction per question: when storing the answer fails, nothing of
    it is kept -- no raw response -- and the old answer stays current."""
    engine_client.fail_on = {1}
    run("start")
    old = _answers(db, is_current=True, status=AnswerStatus.FAILED)[0]
    responses = db.query(DDResponse).count()

    def broken_history(**_fields):
        raise RuntimeError("the history row could not be written")

    monkeypatch.setattr(processor_module, "DDAnswerHistory", broken_history)
    engine_client.fail_on = set()
    run("resume")

    assert len(engine_client.calls) == 4  # OpenAI did answer the question again
    db.expire_all()
    assert db.query(DDResponse).count() == responses
    current = db.query(DDAnswer).filter_by(question_id=old.question_id, is_current=True).one()
    assert (current.id, current.status) == (old.id, AnswerStatus.FAILED)
    assert _execution(db).status == ExecutionStatus.FAILED


def test_a_rate_limit_is_retried_after_the_delay_openai_asks(db, run, engine_client, monkeypatch):
    slept = []
    monkeypatch.setattr(processor_module.time, "sleep", slept.append)
    engine_client.errors = {
        1: openai_error(openai.RateLimitError, 429, headers={"retry-after": "7"})
    }
    run("start")

    assert slept == [7.0]
    assert len(engine_client.calls) == 4  # the first question twice
    answers = _answers(db, is_current=True)
    assert [a.status for a in answers] == [AnswerStatus.COMPLETED] * 3
    assert [a.retry_count for a in answers] == [1, 0, 0]
    assert _execution(db).status == ExecutionStatus.GENERATED


def test_a_refused_key_stops_the_run_at_once(db, run, engine_client):
    """A global error that no retry can fix: the circuit breaker stops the run
    after the first question instead of failing every one of them."""
    engine_client.errors = {1: openai_error(openai.AuthenticationError, 401)}
    run("start")

    assert len(engine_client.calls) == 1
    assert [a.error_type for a in _answers(db)] == [ErrorType.API_ERROR]
    assert _execution(db).status == ExecutionStatus.FAILED


def test_the_text_of_an_openai_error_never_reaches_the_browser(
    client, analyst, auth_headers, run, engine_client
):
    engine_client.errors = {
        1: openai_error(
            openai.AuthenticationError, 401, "Incorrect API key provided: sk-EXAMPLE-1234"
        )
    }
    run("start")

    body = client.get(f"/api/session/{run.session.id}/status", headers=auth_headers(analyst))
    assert "sk-EXAMPLE-1234" not in body.text
    assert "Incorrect API key" not in body.text
    assert "check the OpenAI key" in body.json()["progress"][0]["last_error"]


def test_a_run_that_cannot_go_on_ends_failed(
    db, client, analyst, make_dd_type, make_dd_session, auth_headers, engine_client
):
    """An error of the run itself, not of a question (here: no question at
    all), ends it failed, whether started or resumed."""
    dd_type = make_dd_type(questions=0)
    session = make_dd_session(analyst)
    url = f"/api/processing/session/{session.id}/dd/{dd_type.code}/start"
    assert client.post(url, headers=auth_headers(analyst)).status_code == 200
    assert _execution(db).status == ExecutionStatus.FAILED
