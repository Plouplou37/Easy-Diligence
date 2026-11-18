"""Answers: what the review page lists, the review itself (edit, status, revert,
history) and the export of the current versions."""

import io

import pandas as pd
import pytest

from app.models.answer import AnswerStatus, DDAnswer
from app.models.execution import DDExecution
from app.models.message import DDMessage
from app.models.questions import DDQuestion
from app.models.response import DDResponse
from app.models.vector_store import SessionVectorStore


@pytest.fixture
def answered(db, analyst, make_dd_type, make_dd_session):
    """A generated run of the analyst: two answered questions, and the OpenAI
    response that produced them."""
    dd_type = make_dd_type(questions=2)
    session = make_dd_session(analyst)
    execution = DDExecution(session_id=session.id, dd_type_id=dd_type.id, status="generated")
    db.add(execution)
    db.flush()
    db.add(DDResponse(execution_id=execution.id, response_id="resp_1", openai_response={}))
    db.add(
        DDMessage(
            response_id="resp_1", message_index=0, role="assistant", openai_message_id="msg_1"
        )
    )
    for question in db.query(DDQuestion).order_by(DDQuestion.id):
        db.add(
            DDAnswer(
                session_id=session.id,
                execution_id=execution.id,
                dd_type_id=dd_type.id,
                section_id=question.section_id,
                question_id=question.id,
                section_code="S1",
                question_code=question.question_code,
                answer_text=f"Answer to {question.question_code}",
                sources={"files": [], "web": [], "total_count": 0},
                status=AnswerStatus.COMPLETED,
            )
        )
    db.commit()
    answers = db.query(DDAnswer).order_by(DDAnswer.id).all()
    return session, dd_type, answers


def test_listing_carries_the_review_labels(client, analyst, answered, auth_headers):
    session, dd_type, _ = answered
    response = client.get(f"/api/answers/session/{session.id}", headers=auth_headers(analyst))
    first = response.json()["answers"][0]
    assert first["question_text"] == "Question 1.1?"
    assert first["section_name"] == "Section 1"
    assert first["dd_type_code"] == dd_type.code
    assert first["session_name"] == session.name
    assert first["openai_message_ids"] == ["msg_1"]


def test_an_edit_is_a_new_version_to_review(client, analyst, answered, auth_headers):
    _, _, answers = answered
    headers = auth_headers(analyst)
    response = client.put(
        f"/api/answers/{answers[0].id}",
        json={"answer_text": "Edited", "edit_reason": "Typo"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert (body["version"], body["status"], body["answer_text"]) == (2, "needs_review", "Edited")
    assert body["question_text"] == "Question 1.1?"

    history = client.get(f"/api/answers/{answers[0].id}/history", headers=headers).json()
    assert history["current_version"] == 2
    assert [(v["version"], v["edit_reason"]) for v in history["versions"]] == [(2, "Typo")]


def test_revert_brings_back_an_earlier_version(client, analyst, answered, auth_headers):
    _, _, answers = answered
    headers = auth_headers(analyst)
    url = f"/api/answers/{answers[0].id}"
    client.put(url, json={"answer_text": "First edit"}, headers=headers)
    client.put(url, json={"answer_text": "Second edit"}, headers=headers)

    response = client.post(f"{url}/revert", json={"version": 2}, headers=headers)
    assert response.status_code == 200
    assert (response.json()["version"], response.json()["answer_text"]) == (4, "First edit")

    assert client.post(f"{url}/revert", json={"version": 9}, headers=headers).status_code == 404
    assert client.post(f"{url}/revert", json={}, headers=headers).status_code == 400


def test_status_accepts_only_the_review_verdicts(client, analyst, answered, auth_headers):
    _, _, answers = answered
    headers = auth_headers(analyst)
    url = f"/api/answers/{answers[0].id}/status"

    response = client.patch(url, json={"status": "approved"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["validation_status"] == "approved"
    assert client.patch(url, json={"status": "failed"}, headers=headers).status_code == 400
    assert client.patch(url, json={}, headers=headers).status_code == 400


def test_someone_else_cannot_review(client, make_user, answered, auth_headers):
    _, _, answers = answered
    headers = auth_headers(make_user())
    url = f"/api/answers/{answers[0].id}"
    assert client.put(url, json={"answer_text": "x"}, headers=headers).status_code == 403
    assert client.get(f"{url}/history", headers=headers).status_code == 403
    assert (
        client.put("/api/answers/999", json={"answer_text": "x"}, headers=headers).status_code
        == 404
    )


def test_export_keeps_only_the_current_versions(db, client, analyst, answered, auth_headers):
    """Superseded versions and failed attempts stay in the table: a regenerated
    question used to appear twice in the report."""
    session, dd_type, answers = answered
    old = answers[0]
    db.add(
        DDAnswer(
            session_id=session.id,
            execution_id=old.execution_id,
            dd_type_id=dd_type.id,
            section_id=old.section_id,
            question_id=old.question_id,
            section_code="S1",
            question_code=old.question_code,
            answer_text="Old attempt",
            status=AnswerStatus.FAILED,
            is_current=False,
        )
    )
    db.commit()

    response = client.get(
        f"/api/answers/session/{session.id}/export?format=excel", headers=auth_headers(analyst)
    )
    rows = pd.read_excel(io.BytesIO(response.content), sheet_name="All Answers")
    assert len(rows) == 2
    assert "Old attempt" not in rows.to_string()


def test_regenerate_with_a_document(
    db, client, analyst, answered, auth_headers, fake_vector_stores, monkeypatch
):
    """The document goes into a new store for the session and this DD type,
    and the engine gets it as a source, with the instruction and the company."""
    import app.engine.processor as processor_module

    session, dd_type, answers = answered
    seen = {}

    def regenerate(self, db, answer, store_ids, company, instruction, url, extra_source):
        seen.update(
            store_ids=store_ids, company=company, instruction=instruction, extra=extra_source
        )
        answer.answer_text = "Regenerated"
        db.commit()
        return answer

    monkeypatch.setattr(processor_module, "OpenAIProcessor", lambda: None)
    monkeypatch.setattr(processor_module.DDProcessor, "regenerate_single_answer", regenerate)

    response = client.post(
        f"/api/answers/{answers[0].id}/regenerate",
        data={"instruction": "  Be brief  "},
        files={"file": ("memo.pdf", b"%PDF-1.7", "application/pdf")},
        headers=auth_headers(analyst),
    )
    assert response.status_code == 200
    assert response.json()["answer_text"] == "Regenerated"
    assignment = db.query(SessionVectorStore).one()
    assert assignment.dd_type_id == dd_type.id
    assert seen["store_ids"] == [assignment.vector_store_id]
    assert seen["instruction"] == "Be brief"
    assert seen["extra"]["filename"] == "memo.pdf"
    assert seen["company"]["name"] == "Example Asia Fund"
    assert ("upload_file", "memo.pdf") in fake_vector_stores.calls
