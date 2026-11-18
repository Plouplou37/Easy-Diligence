"""Stored summaries: listing and hand edits (generating them needs OpenAI)."""

import pytest

from app.models.summary import DDSummary


@pytest.fixture
def summarised(db, analyst, make_dd_type, make_dd_session):
    """A session of the analyst with a synthesis on each of two DD types."""
    session = make_dd_session(analyst)
    first, second = make_dd_type(), make_dd_type()
    for dd_type in (first, second):
        db.add(
            DDSummary(
                session_id=session.id, dd_type_id=dd_type.id, summary_text=f"About {dd_type.code}"
            )
        )
    db.commit()
    return session, first


def test_list_all_or_one_dd_type(client, analyst, summarised, auth_headers):
    session, first = summarised
    headers = auth_headers(analyst)
    url = f"/api/summaries/session/{session.id}"
    assert len(client.get(url, headers=headers).json()) == 2
    only = client.get(f"{url}?dd_type={first.code}", headers=headers).json()
    assert [s["dd_type_code"] for s in only] == [first.code]


def test_edit(db, client, analyst, summarised, auth_headers):
    session, _ = summarised
    summary = db.query(DDSummary).first()
    response = client.put(
        f"/api/summaries/{summary.id}",
        json={"summary_text": "Edited"},
        headers=auth_headers(analyst),
    )
    assert response.status_code == 200
    assert (response.json()["summary_text"], response.json()["edited_by"]) == ("Edited", analyst.id)


def test_someone_else_cannot_read_or_edit(db, client, make_user, summarised, auth_headers):
    session, _ = summarised
    headers = auth_headers(make_user())
    summary = db.query(DDSummary).first()
    assert client.get(f"/api/summaries/session/{session.id}", headers=headers).status_code == 403
    response = client.put(
        f"/api/summaries/{summary.id}", json={"summary_text": "x"}, headers=headers
    )
    assert response.status_code == 403
