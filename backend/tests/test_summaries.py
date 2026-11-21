"""Summaries: listing, hand edits, and generating them (OpenAI replaced by a fake)."""

import threading

import pytest

import app.engine.summarizer as summarizer
from app.engine.answers import new_answer
from app.models.execution import DDExecution
from app.models.questions import DDQuestion
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


class FakeSummaries:
    """Stands in for OpenAIProcessor.generate_summary: a text per prompt, and
    the threads it was called from."""

    def __init__(self):
        self.threads = {"Summary": set(), "Synthesis": set()}

    def generate_summary(self, system_prompt, user_prompt, max_output_tokens):
        kind = "Synthesis" if "overall synthesis" in user_prompt else "Summary"
        self.threads[kind].add(threading.get_ident())
        return f"{kind} of {len(user_prompt)} characters"


def test_generate_writes_a_summary_per_section_and_the_synthesis(
    db, client, analyst, make_dd_type, make_dd_session, auth_headers, monkeypatch
):
    """Synchronous now: the section summaries are asked in parallel threads,
    the rows are written by the request's own thread."""
    fake = FakeSummaries()
    monkeypatch.setattr(summarizer, "OpenAIProcessor", lambda: fake)
    dd_type, session = make_dd_type(sections=3, questions=2), make_dd_session(analyst)
    execution = DDExecution(session_id=session.id, dd_type_id=dd_type.id)
    db.add(execution)
    db.flush()
    for question in db.query(DDQuestion):
        db.add(new_answer(execution, question, answer_text="An answer"))
    db.commit()

    url = f"/api/summaries/session/{session.id}/dd/{dd_type.code}/generate"
    response = client.post(url, headers=auth_headers(analyst))

    assert response.status_code == 200, response.text
    rows = response.json()
    assert [row["section_id"] is None for row in rows] == [False, False, False, True]
    assert rows[-1]["summary_text"].startswith("Synthesis")
    assert db.query(DDSummary).count() == 4
    # The synthesis is asked by the request's thread, the sections by others.
    assert fake.threads["Synthesis"].isdisjoint(fake.threads["Summary"])
