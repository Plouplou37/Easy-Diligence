"""Sessions: creation, reading, progress of the runs, listing, deletion."""

import json

from app.models.answer import AnswerStatus, DDAnswer
from app.models.execution import DDExecution, ExecutionStatus
from app.models.questions import DDQuestion
from app.models.session import DDSession, SessionStatus


def test_create_selects_only_the_types_the_user_can_see(
    db, client, make_user, make_company, make_dd_type, auth_headers
):
    alice, bob = make_user(), make_user()
    shared, own = make_dd_type(None), make_dd_type(alice)
    make_dd_type(bob)  # private to bob: never offered to alice
    inactive = make_dd_type(None)
    inactive.is_active = False
    db.commit()

    response = client.post(
        "/api/session/",
        json={"company_id": make_company(alice).id, "name": "Review"},
        headers=auth_headers(alice),
    )
    assert response.status_code == 200
    codes = {t["code"] for t in json.loads(response.json()["dd_types_json"])}
    assert codes == {shared.code, own.code}
    assert response.json()["session_code"].startswith("REV-")


def test_create_on_someone_elses_company_is_refused(client, make_user, make_company, auth_headers):
    response = client.post(
        "/api/session/",
        json={"company_id": make_company(make_user()).id, "name": "Review"},
        headers=auth_headers(make_user()),
    )
    assert response.status_code == 404


def test_read_by_id_or_code(client, analyst, make_dd_session, auth_headers):
    session = make_dd_session(analyst)
    headers = auth_headers(analyst)
    assert client.get(f"/api/session/{session.id}", headers=headers).json()["id"] == session.id
    by_code = client.get(f"/api/session/{session.session_code}", headers=headers)
    assert by_code.json()["id"] == session.id
    assert client.get("/api/session/UNKNOWN-CODE", headers=headers).status_code == 404


def test_status_shows_the_progress_of_each_run(
    db, client, analyst, make_dd_type, make_dd_session, auth_headers
):
    dd_type = make_dd_type(questions=2)
    session = make_dd_session(analyst)
    execution = DDExecution(
        session_id=session.id, dd_type_id=dd_type.id, status=ExecutionStatus.GENERATED
    )
    db.add(execution)
    db.flush()
    for question in db.query(DDQuestion):
        db.add(
            DDAnswer(
                session_id=session.id,
                execution_id=execution.id,
                dd_type_id=dd_type.id,
                section_id=question.section_id,
                question_id=question.id,
                section_code="S1",
                question_code=question.question_code,
                answer_text="An answer",
                sources={"files": [{"filename": "prospectus.pdf"}], "web": []},
                tokens_used=100,
                status=AnswerStatus.COMPLETED,
            )
        )
    db.commit()

    body = client.get(f"/api/session/{session.id}/status", headers=auth_headers(analyst)).json()
    progress = body["progress"][0]
    assert progress["dd_type"] == dd_type.code
    assert progress["status"] == "completed"  # generated, from the user's point of view
    assert (progress["questions_completed"], progress["total_questions"]) == (2, 2)
    assert progress["percentage"] == 100
    assert progress["tokens_used"] == 200
    assert progress["answers_with_documents"] == 2
    assert progress["sections_progress"][0]["status"] == "completed"


def test_status_of_a_session_never_run(client, analyst, make_dd_session, auth_headers):
    session = make_dd_session(analyst)
    body = client.get(f"/api/session/{session.id}/status", headers=auth_headers(analyst)).json()
    assert body["progress"] == []


def test_listing_refuses_an_unknown_status(client, analyst, auth_headers):
    response = client.get("/api/session/?status=archived", headers=auth_headers(analyst))
    assert response.status_code == 400


def test_only_the_creator_deletes_and_not_while_running(
    db, client, make_user, make_dd_session, auth_headers
):
    owner, assignee = make_user(), make_user()
    session = make_dd_session(owner, assignee=assignee)
    session_id = session.id
    url = f"/api/session/{session_id}"

    assert client.delete(url, headers=auth_headers(assignee)).status_code == 403

    session.status = SessionStatus.IN_PROGRESS
    db.commit()
    assert client.delete(url, headers=auth_headers(owner)).status_code == 400

    session.status = SessionStatus.PAUSED
    db.commit()
    assert client.delete(url, headers=auth_headers(owner)).status_code == 200
    db.expire_all()
    assert db.get(DDSession, session_id) is None
