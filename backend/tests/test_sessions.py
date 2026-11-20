"""Sessions: creation, reading, progress of the runs, listing, deletion."""

import pytest

from app.models.answer import AnswerStatus, DDAnswer
from app.models.execution import DDExecution, ExecutionStatus
from app.models.questions import DDQuestion
from app.models.session import DDSession, SessionDDType


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
    assert {t["code"] for t in response.json()["dd_types"]} == {shared.code, own.code}
    assert response.json()["session_code"].startswith("REV-")


def test_the_dd_types_chosen_keep_their_order(
    db, client, analyst, make_company, make_dd_type, auth_headers
):
    first, second, third = make_dd_type(), make_dd_type(), make_dd_type()
    response = client.post(
        "/api/session/",
        json={
            "company_id": make_company(analyst).id,
            "name": "Review",
            "dd_type_ids": [third.id, first.id],
        },
        headers=auth_headers(analyst),
    )
    assert [t["code"] for t in response.json()["dd_types"]] == [third.code, first.code]
    links = db.query(SessionDDType).order_by(SessionDDType.position).all()
    assert [(link.dd_type_id, link.position) for link in links] == [(third.id, 0), (first.id, 1)]
    assert second.id not in {link.dd_type_id for link in links}


def test_a_renamed_dd_type_shows_under_its_new_name(
    db, client, analyst, make_dd_type, make_dd_session, auth_headers
):
    dd_type, session = make_dd_type(), make_dd_session(analyst)
    db.add(SessionDDType(session_id=session.id, dd_type_id=dd_type.id, position=0))
    dd_type.name = "Renamed questionnaire"
    db.commit()

    body = client.get(f"/api/session/{session.id}", headers=auth_headers(analyst)).json()
    assert body["dd_types"] == [
        {"id": dd_type.id, "code": dd_type.code, "name": "Renamed questionnaire"}
    ]


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


def test_only_the_creator_deletes(db, client, make_user, make_dd_session, auth_headers):
    owner, assignee = make_user(), make_user()
    session = make_dd_session(owner, assignee=assignee)
    session_id = session.id
    url = f"/api/session/{session_id}"

    assert client.delete(url, headers=auth_headers(assignee)).status_code == 403
    assert client.delete(url, headers=auth_headers(owner)).status_code == 200
    db.expire_all()
    assert db.get(DDSession, session_id) is None


@pytest.fixture
def two_types_session(db, analyst, make_dd_type, make_dd_session):
    """A session of the analyst with two DD types chosen, and a helper that
    sets the status of each one's run."""
    session = make_dd_session(analyst)
    first, second = make_dd_type(), make_dd_type()
    for position, dd_type in enumerate((first, second)):
        db.add(SessionDDType(session_id=session.id, dd_type_id=dd_type.id, position=position))
    db.commit()

    def runs(*statuses):
        for dd_type, status in zip((first, second), statuses, strict=False):
            db.add(DDExecution(session_id=session.id, dd_type_id=dd_type.id, status=status))
        db.commit()

    return session, runs


@pytest.mark.parametrize(
    ("statuses", "refused"),
    [
        ((ExecutionStatus.IN_PROGRESS,), "while one of its DD types is running"),
        ((ExecutionStatus.GENERATED, ExecutionStatus.VALIDATED), "completed session"),
    ],
)
def test_a_running_or_completed_session_is_not_deleted(
    client, analyst, auth_headers, two_types_session, statuses, refused
):
    session, runs = two_types_session
    runs(*statuses)
    response = client.delete(f"/api/session/{session.id}", headers=auth_headers(analyst))
    assert response.status_code == 400
    assert refused in response.json()["detail"]


@pytest.mark.parametrize(
    "statuses",
    [
        (),  # never run
        (ExecutionStatus.PAUSED,),
        (ExecutionStatus.GENERATED, ExecutionStatus.FAILED),
        (ExecutionStatus.GENERATED,),  # the second DD type not run yet
    ],
)
def test_a_session_not_running_nor_completed_is_deleted(
    db, client, analyst, auth_headers, two_types_session, statuses
):
    session, runs = two_types_session
    runs(*statuses)
    response = client.delete(f"/api/session/{session.id}", headers=auth_headers(analyst))
    assert response.status_code == 200
    assert db.query(SessionDDType).count() == 0  # the links go with it
