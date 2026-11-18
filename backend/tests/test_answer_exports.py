"""Answer exports: the PDF / Excel builders, and the export endpoint."""

import io
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pandas as pd
import pytest

from app.exports.answers import AnswerExporter
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


def _make_answer(
    i=0,
    sources='[{"type": "document", "content": "Test source"}]',
    section_code=None,
    status=AnswerStatus.COMPLETED,
    confidence=0.9,
):
    """A DDAnswer with its question, section and DD type as mocks: the
    builders only read attributes, no database is needed."""
    answer = DDAnswer(
        id=i + 1,
        question_code=f"Q{i + 1}",
        answer_text=f"Test Answer {i + 1}",
        section_code=section_code or f"SEC{i + 1}",
        confidence_score=confidence,
        status=status,
        tokens_used=100,
        created_at=datetime.now(UTC),
        sources=sources,
    )
    answer.dd_type_obj = MagicMock()
    answer.dd_type_obj.name = f"DD Type {i + 1}"
    answer.question = MagicMock()
    answer.question.question_text = f"Test Question {i + 1}?"
    answer.section = MagicMock()
    answer.section.title = f"Section {i + 1}"
    return answer


def _excel_rows(response) -> pd.DataFrame:
    """The "All Answers" sheet (the first one describes the session)."""
    return pd.read_excel(io.BytesIO(response.body), sheet_name="All Answers")


class TestBuilders:
    @pytest.fixture
    def session(self):
        return DDSession(
            id=1,
            name="Test Session",
            description="Test Description",
            company=Company(id=1, name="Test Company"),
            created_at=datetime.now(UTC),
        )

    def test_pdf_report(self, session):
        response = AnswerExporter.generate_pdf_report(session, [_make_answer(i) for i in range(3)])
        assert response.media_type == "application/pdf"
        # Spaces become underscores for a safe Content-Disposition filename.
        assert "Test_Session_DD_Report.pdf" in response.headers["Content-Disposition"]
        assert response.body.startswith(b"%PDF")

    def test_excel_report(self, session):
        response = AnswerExporter.generate_excel_report(
            session, [_make_answer(i) for i in range(3)]
        )
        assert response.media_type == (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert "Test Session_DD_Report.xlsx" in response.headers["Content-Disposition"]
        assert len(_excel_rows(response)) == 3

    def test_reports_without_answers(self, session):
        assert AnswerExporter.generate_pdf_report(session, []).body.startswith(b"%PDF")
        assert len(AnswerExporter.generate_excel_report(session, []).body) > 0

    def test_excel_lists_the_engine_sources(self, session):
        """The engine stores sources as a dict: the Excel export used to iterate
        it as a list and crashed on every sourced answer."""
        response = AnswerExporter.generate_excel_report(
            session, [_make_answer(0, sources=ENGINE_SOURCES)]
        )
        sources = _excel_rows(response).iloc[0]["Sources"]
        assert "Document: prospectus.pdf" in sources
        assert "Web: https://example.com/fund" in sources

    def test_excel_survives_malformed_sources(self, session):
        response = AnswerExporter.generate_excel_report(
            session, [_make_answer(0, sources="invalid json", status=AnswerStatus.NEEDS_REVIEW)]
        )
        assert len(_excel_rows(response)) == 1

    def test_pdf_with_web_sources(self, session):
        answer = _make_answer(0, sources=ENGINE_SOURCES)
        assert AnswerExporter.generate_pdf_report(session, [answer]).body.startswith(b"%PDF")

    @staticmethod
    def _table(columns, rows=5):
        """A markdown table with one short column and long ones, as the model writes."""
        header = ["Period"] + [f"Very long column heading number {c}" for c in range(1, columns)]
        body = [
            ["Q1"] + ["A rather long cell value that weighs heavily"] * (columns - 1)
            for _ in range(rows)
        ]
        lines = [header, ["---"] * columns] + body
        return "\n".join("| " + " | ".join(line) + " |" for line in lines)

    def test_pdf_with_a_wide_markdown_table(self, session):
        """11 columns once gave a short column less width than its padding."""
        answer = _make_answer(0)
        answer.answer_text = "Performance:\n\n" + self._table(11)
        assert AnswerExporter.generate_pdf_report(session, [answer]).body.startswith(b"%PDF")

    def test_pdf_with_an_undrawable_markdown_table(self, session):
        """Too many columns to draw: written as text lines, the export still succeeds."""
        answer = _make_answer(0)
        answer.answer_text = self._table(50, rows=2)
        assert AnswerExporter.generate_pdf_report(session, [answer]).body.startswith(b"%PDF")


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
                section_code="S1",
                question_code=question.question_code,
                answer_text="**Answer** with sources",
                sources=ENGINE_SOURCES,
                status=AnswerStatus.COMPLETED,
            )
        )
    db.commit()
    return session


@pytest.mark.parametrize(
    ("fmt", "media_type"),
    [
        ("pdf", "application/pdf"),
        ("excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    ],
)
def test_export(client, analyst, answered_session, auth_headers, fmt, media_type):
    response = client.get(
        f"/api/answers/session/{answered_session.id}/export?format={fmt}",
        headers=auth_headers(analyst),
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(media_type)


def test_export_by_session_code(client, analyst, answered_session, auth_headers):
    response = client.get(
        f"/api/answers/session/{answered_session.session_code}/export?format=pdf",
        headers=auth_headers(analyst),
    )
    assert response.status_code == 200


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


def test_export_in_an_unknown_format(client, analyst, answered_session, auth_headers):
    response = client.get(
        f"/api/answers/session/{answered_session.id}/export?format=docx",
        headers=auth_headers(analyst),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Format must be 'pdf' or 'excel'"


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
