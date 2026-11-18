"""The PDF report: the builder, its sources, and the export endpoint."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.exports import pdf
from app.exports.sources import format_sources
from app.models.answer import AnswerStatus, DDAnswer
from app.models.company import Company
from app.models.execution import DDExecution
from app.models.questions import DDQuestion
from app.models.session import DDSession

# The shape the engine stores (engine/openai_client.py).
ENGINE_SOURCES = {
    "files": [{"type": "file_search", "filename": "prospectus.pdf"}],
    "web": [{"type": "web_search", "url": "https://example.com/fund"}],
    "total_count": 2,
}


def _make_answer(i=0, sources=None, status=AnswerStatus.COMPLETED):
    """A DDAnswer with its question, section and DD type as mocks: the builder
    only reads attributes, no database is needed."""
    answer = DDAnswer(
        id=i + 1,
        session_id=1,
        question_code=f"A.{i + 1:02d}",
        answer_text=f"Test Answer {i + 1}",
        section_code="A",
        status=status,
        tokens_used=100,
        created_at=datetime.now(UTC),
        sources=sources,
    )
    answer.dd_type_obj = MagicMock()
    answer.dd_type_obj.name = "Operational DD"
    answer.question = MagicMock()
    answer.question.question_text = f"Test Question {i + 1}?"
    answer.section = MagicMock()
    answer.section.title = "General"
    return answer


@pytest.fixture
def session():
    return DDSession(
        id=1,
        name="Test Session",
        company_id=1,
        company=Company(id=1, name="Example Asia Fund"),
        created_at=datetime.now(UTC),
    )


def test_report(session):
    content = pdf.build_report(session, [_make_answer(i) for i in range(3)])
    assert content.startswith(b"%PDF")
    # Spaces become underscores, for a safe Content-Disposition file name.
    assert pdf.report_filename(session) == "Test_Session_DD_Report.pdf"


def test_report_without_answers(session):
    assert pdf.build_report(session, []).startswith(b"%PDF")


def test_sources_of_the_engine_are_listed():
    lines = format_sources(ENGINE_SOURCES)
    assert lines[0] == "1. Document &mdash; prospectus.pdf"
    assert "https://example.com/fund" in lines[1]


def test_malformed_sources_do_not_break_the_report(session):
    answer = _make_answer(0, sources="invalid json", status=AnswerStatus.NEEDS_REVIEW)
    assert pdf.build_report(session, [answer]).startswith(b"%PDF")


def _table(columns, rows=5):
    """A markdown table with one short column and long ones, as the model writes."""
    header = ["Period"] + [f"Very long column heading number {c}" for c in range(1, columns)]
    body = [
        ["Q1"] + ["A rather long cell value that weighs heavily"] * (columns - 1)
        for _ in range(rows)
    ]
    lines = [header, ["---"] * columns] + body
    return "\n".join("| " + " | ".join(line) + " |" for line in lines)


def test_a_wide_markdown_table(session):
    """11 columns once gave a short column less width than its padding."""
    answer = _make_answer(0)
    answer.answer_text = "Performance:\n\n" + _table(11)
    assert pdf.build_report(session, [answer]).startswith(b"%PDF")


def test_an_undrawable_markdown_table(session):
    """Too many columns to draw: written as text lines, the export still succeeds."""
    answer = _make_answer(0)
    answer.answer_text = _table(50, rows=2)
    assert pdf.build_report(session, [answer]).startswith(b"%PDF")


def test_the_charter_colours_must_be_hex():
    with pytest.raises(ValidationError):
        Settings(pdf_primary_color="navy")
    assert Settings(pdf_primary_color="#112233").pdf_primary_color == "#112233"


# --- The endpoint ---------------------------------------------------------------


@pytest.fixture
def answered_session(db, analyst, make_dd_type, make_dd_session):
    """A session of the analyst with one answered question per question."""
    dd_type = make_dd_type(questions=2)
    session = make_dd_session(analyst)
    execution = DDExecution(session_id=session.id, dd_type_id=dd_type.id, status="generated")
    db.add(execution)
    db.flush()
    for question in db.query(DDQuestion).order_by(DDQuestion.id):
        db.add(
            DDAnswer(
                session_id=session.id,
                execution_id=execution.id,
                dd_type_id=dd_type.id,
                section_id=question.section_id,
                question_id=question.id,
                section_code="A",
                question_code=question.question_code,
                answer_text="**Answer** with sources",
                sources=ENGINE_SOURCES,
                status=AnswerStatus.COMPLETED,
            )
        )
    db.commit()
    return session


def test_export(client, analyst, answered_session, auth_headers):
    response = client.get(
        f"/api/answers/session/{answered_session.id}/export", headers=auth_headers(analyst)
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "_DD_Report.pdf" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")


def test_export_by_session_code(client, analyst, answered_session, auth_headers):
    response = client.get(
        f"/api/answers/session/{answered_session.session_code}/export?format=pdf",
        headers=auth_headers(analyst),
    )
    assert response.status_code == 200


def test_there_is_no_excel_export(client, analyst, answered_session, auth_headers):
    response = client.get(
        f"/api/answers/session/{answered_session.id}/export?format=excel",
        headers=auth_headers(analyst),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Only the PDF export is available"


def test_export_of_an_unknown_session(client, analyst, auth_headers):
    response = client.get("/api/answers/session/999/export", headers=auth_headers(analyst))
    assert response.status_code == 404


def test_export_without_answers(client, analyst, make_dd_session, auth_headers):
    session = make_dd_session(analyst)
    response = client.get(
        f"/api/answers/session/{session.id}/export", headers=auth_headers(analyst)
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "No answers found for session"


def test_export_of_someone_elses_session(client, make_user, answered_session, auth_headers):
    response = client.get(
        f"/api/answers/session/{answered_session.id}/export", headers=auth_headers(make_user())
    )
    assert response.status_code == 403


def test_answer_list_and_stats(client, analyst, answered_session, auth_headers):
    headers = auth_headers(analyst)
    listing = client.get(f"/api/answers/session/{answered_session.id}", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()["answers"]) == 2

    everything = client.get("/api/answers/all", headers=headers)
    assert everything.status_code == 200
    assert everything.json()["pagination"]["total_items"] == 2

    stats = client.get("/api/answers/stats", headers=headers)
    assert stats.status_code == 200
    assert {"total_answers", "status_counts", "recent_activity"} <= stats.json().keys()
