"""DD types and their structure: import, changes, validation lock, sections and
questions with their codes."""

import json

import pytest

from app.models.dd_types import DDType
from app.models.execution import DDExecution
from app.models.questions import DDQuestion, DDSection

QUESTIONNAIRE = [
    {"section": "General", "questions": [{"text": "Name?", "ref": "A.01"}, "Launch date?"]},
    {"section": "Team", "questions": ["Team size?"]},
]


def _import(client, headers, code="ODD", data=QUESTIONNAIRE):
    return client.post(
        "/api/dd-types/import",
        data={"code": code, "name": "Operational DD"},
        files={"file": ("odd.json", json.dumps(data).encode(), "application/json")},
        headers=headers,
    )


def test_import_builds_the_structure_with_its_codes(db, client, analyst, auth_headers):
    response = _import(client, auth_headers(analyst))
    assert response.status_code == 200, response.text
    assert response.json()["created_by"] == analyst.id

    sections = db.query(DDSection).order_by(DDSection.order_index).all()
    assert [s.section_code for s in sections] == ["A", "B"]
    codes = [[q.question_code for q in s.questions] for s in sections]
    assert codes == [["A.01", "A.02"], ["B.01"]]


def test_import_refusals(client, analyst, auth_headers):
    headers = auth_headers(analyst)
    _import(client, headers)
    assert _import(client, headers).status_code == 400  # code taken
    bad = client.post(
        "/api/dd-types/import",
        data={"code": "BAD", "name": "Bad"},
        files={"file": ("bad.json", b"not json", "application/json")},
        headers=headers,
    )
    assert bad.status_code == 400
    assert "File parsing error" in bad.json()["detail"]


def test_changing_someone_elses_dd_type(client, make_user, make_dd_type, auth_headers):
    """A private type of someone else is invisible (404); a shared one is
    visible but not theirs to change (403)."""
    headers = auth_headers(make_user())
    private, shared = make_dd_type(make_user()), make_dd_type(None)
    assert (
        client.put(f"/api/dd-types/{private.code}", json={"name": "x"}, headers=headers).status_code
        == 404
    )
    assert (
        client.put(f"/api/dd-types/{shared.code}", json={"name": "x"}, headers=headers).status_code
        == 403
    )


def test_update_activate_and_delete(db, client, analyst, make_dd_type, auth_headers):
    headers = auth_headers(analyst)
    dd_type = make_dd_type(analyst)
    dd_type_id = dd_type.id
    url = f"/api/dd-types/{dd_type.code}"

    assert client.put(url, json={"name": "Renamed"}, headers=headers).json()["name"] == "Renamed"
    client.post(f"{url}/deactivate", headers=headers)
    db.expire_all()
    assert db.get(DDType, dd_type_id).is_active is False

    assert client.delete(url, headers=headers).status_code == 200
    db.expire_all()
    assert db.get(DDType, dd_type_id) is None
    assert db.query(DDQuestion).count() == 0  # its structure goes with it


def test_a_dd_type_that_has_run_cannot_be_deleted(
    db, client, analyst, make_dd_type, make_dd_session, auth_headers
):
    dd_type = make_dd_type(analyst)
    db.add(DDExecution(session_id=make_dd_session(analyst).id, dd_type_id=dd_type.id))
    db.commit()
    response = client.delete(f"/api/dd-types/{dd_type.code}", headers=auth_headers(analyst))
    assert response.status_code == 409


# --- Sections and questions ----------------------------------------------------------


@pytest.fixture
def own_type(analyst, make_dd_type):
    """A questionnaire of the analyst: sections A and B, questions A.01, A.02, B.01, B.02."""
    return make_dd_type(analyst, sections=2, questions=2)


def test_a_new_section_takes_the_next_letter_and_place(db, client, analyst, own_type, auth_headers):
    response = client.post(
        f"/api/questions/dd-types/{own_type.code}/sections",
        json={"title": "Risk"},
        headers=auth_headers(analyst),
    )
    assert response.status_code == 200
    assert response.json()["section_code"] == "C"
    assert response.json()["order_index"] == 2


def test_the_first_section_goes_first(client, analyst, make_dd_type, auth_headers):
    """`max or -1` put a section after one at 0 at 0 again."""
    dd_type = make_dd_type(analyst, sections=0)
    headers = auth_headers(analyst)
    url = f"/api/questions/dd-types/{dd_type.code}/sections"
    first = client.post(url, json={"title": "One"}, headers=headers).json()
    second = client.post(url, json={"title": "Two"}, headers=headers).json()
    assert (first["order_index"], second["order_index"]) == (0, 1)
    assert (first["section_code"], second["section_code"]) == ("A", "B")


def test_a_new_question_takes_the_next_code(client, analyst, own_type, auth_headers):
    headers = auth_headers(analyst)
    section = next(s for s in own_type.sections if s.section_code == "A")
    url = f"/api/questions/dd-types/{own_type.code}/sections/{section.id}/questions"

    response = client.post(url, json={"question_text": "Fees?", "order_index": 2}, headers=headers)
    assert response.json()["question_code"] == "A.03"
    duplicate = client.post(
        url, json={"question_text": "Again?", "question_code": "A.01"}, headers=headers
    )
    assert duplicate.status_code == 400

    listed = client.get(url, headers=headers).json()
    assert [q["question_code"] for q in listed] == ["A.01", "A.02", "A.03"]


def test_reorder_swaps_two_questions(client, analyst, own_type, auth_headers):
    section = next(s for s in own_type.sections if s.section_code == "A")
    first = next(q for q in section.questions if q.order_index == 0)
    response = client.patch(
        f"/api/questions/questions/{first.id}/reorder",
        json={"new_order": 1},
        headers=auth_headers(analyst),
    )
    assert response.json()["order_index"] == 1


def test_a_validated_dd_type_is_frozen(client, analyst, own_type, auth_headers):
    headers = auth_headers(analyst)
    assert client.put(f"/api/dd-types/{own_type.code}/validate", headers=headers).status_code == 200
    assert client.put(f"/api/dd-types/{own_type.code}/validate", headers=headers).status_code == 400

    question = own_type.sections[0].questions[0]
    response = client.put(
        f"/api/questions/questions/{question.id}", json={"question_text": "x"}, headers=headers
    )
    assert response.status_code == 400
    assert "immutable" in response.json()["detail"]


def test_someone_else_cannot_edit_the_structure(client, make_user, own_type, auth_headers):
    question = own_type.sections[0].questions[0]
    response = client.delete(
        f"/api/questions/questions/{question.id}", headers=auth_headers(make_user())
    )
    assert response.status_code == 404  # a private type of someone else is not even visible


def test_the_structure_comes_in_order(client, analyst, own_type, auth_headers):
    body = client.get(
        f"/api/questions/dd-types/{own_type.code}", headers=auth_headers(analyst)
    ).json()
    assert [s["section_code"] for s in body["sections"]] == ["A", "B"]
    assert [q["question_code"] for q in body["sections"][0]["questions"]] == ["A.01", "A.02"]
