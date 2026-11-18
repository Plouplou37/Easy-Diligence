"""
Test suite for answer export functionality
Validates that PDF/Excel exports work after modularization
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.exports.answers import AnswerExporter
from app.main import app
from app.models.answer import AnswerStatus, DDAnswer
from app.models.company import Company
from app.models.session import DDSession
from app.models.user import User


def _make_answer(
    i=0,
    sources='[{"type": "document", "content": "Test source"}]',
    section_code=None,
    status=AnswerStatus.COMPLETED,
    confidence=0.9,
):
    """Build a DDAnswer with related question/section/dd_type mocks.

    Question text lives on the DDQuestion relationship and the section title on
    the DDSection relationship (not on DDAnswer itself), so they are attached as
    mocks rather than passed to the constructor.
    """
    answer = DDAnswer(
        id=i + 1,
        question_code=f"Q{i + 1}",
        answer_text=f"Test Answer {i + 1}",
        section_code=section_code or f"SEC{i + 1}",
        confidence_score=confidence,
        status=status,
        tokens_used=100,
        created_at=datetime.utcnow(),
        sources=sources,
    )
    answer.dd_type_obj = MagicMock(name=f"DD Type {i + 1}")
    answer.dd_type_obj.name = f"DD Type {i + 1}"
    answer.question = MagicMock()
    answer.question.question_text = f"Test Question {i + 1}?"
    answer.section = MagicMock()
    answer.section.title = f"Section {i + 1}"
    return answer


class TestAnswerExporter:
    """Test the extracted AnswerExporter class"""

    @pytest.fixture
    def mock_session(self):
        company = Company(id=1, name="Test Company")
        return DDSession(
            id=1,
            name="Test Session",
            description="Test Description",
            company=company,
            created_at=datetime.utcnow(),
        )

    @pytest.fixture
    def mock_answers(self):
        return [_make_answer(i) for i in range(3)]

    def test_generate_pdf_report(self, mock_session, mock_answers):
        """Test PDF report generation"""
        response = AnswerExporter.generate_pdf_report(mock_session, mock_answers)

        # Assertions
        assert response.media_type == "application/pdf"
        assert "attachment" in response.headers["Content-Disposition"]
        # Spaces are sanitised to underscores for a safe Content-Disposition filename
        assert "Test_Session_DD_Report.pdf" in response.headers["Content-Disposition"]
        assert len(response.body) > 0  # Should have PDF content

    def test_generate_excel_report(self, mock_session, mock_answers):
        """Test Excel report generation"""
        response = AnswerExporter.generate_excel_report(mock_session, mock_answers)

        # Assertions
        assert (
            response.media_type
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert "attachment" in response.headers["Content-Disposition"]
        assert "Test Session_DD_Report.xlsx" in response.headers["Content-Disposition"]
        assert len(response.body) > 0  # Should have Excel content

    def test_pdf_report_handles_empty_answers(self, mock_session):
        """Test PDF generation with no answers"""
        response = AnswerExporter.generate_pdf_report(mock_session, [])

        # Should still generate a PDF with session info
        assert response.media_type == "application/pdf"
        assert len(response.body) > 0

    def test_excel_report_handles_empty_answers(self, mock_session):
        """Test Excel generation with no answers"""
        response = AnswerExporter.generate_excel_report(mock_session, [])

        # Should still generate an Excel with session info
        assert (
            response.media_type
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert len(response.body) > 0

    def test_pdf_report_handles_json_sources(self, mock_session):
        """Test PDF generation with various source formats"""
        answer = _make_answer(
            0,
            sources='[{"type": "url", "content": "https://example.com", "url": "https://example.com"}]',
        )

        response = AnswerExporter.generate_pdf_report(mock_session, [answer])

        assert response.media_type == "application/pdf"
        assert len(response.body) > 0

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

    def test_pdf_report_handles_wide_markdown_table(self, mock_session):
        """11 columns once gave a short column less width than its padding: export crashed"""
        answer = _make_answer(0)
        answer.answer_text = "Performance:\n\n" + self._table(11)

        response = AnswerExporter.generate_pdf_report(mock_session, [answer])

        assert response.media_type == "application/pdf"
        assert len(response.body) > 0

    def test_pdf_report_handles_undrawable_markdown_table(self, mock_session):
        """Too many columns to draw: written as text lines, the export still succeeds"""
        answer = _make_answer(0)
        answer.answer_text = self._table(50, rows=2)

        response = AnswerExporter.generate_pdf_report(mock_session, [answer])

        assert response.media_type == "application/pdf"
        assert len(response.body) > 0

    def test_excel_report_handles_malformed_sources(self, mock_session):
        """Test Excel generation with malformed source JSON"""
        answer = _make_answer(
            0,
            sources="invalid json",  # Malformed JSON
            status=AnswerStatus.NEEDS_REVIEW,
            confidence=0.7,
        )

        response = AnswerExporter.generate_excel_report(mock_session, [answer])

        # Should handle malformed JSON gracefully
        assert (
            response.media_type
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert len(response.body) > 0


class TestAnswerExportEndpoint:
    """Test the answer export endpoint after modularization"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def mock_db(self):
        db = MagicMock(spec=Session)
        return db

    @pytest.fixture
    def mock_user(self):
        return User(id=1, email="test@example.com", username="testuser", role="user")

    @pytest.fixture
    def mock_session(self):
        company = Company(id=1, name="Test Company")
        return DDSession(
            id=1,
            name="Test Export Session",
            description="Test Description",
            company=company,
            created_at=datetime.utcnow(),
        )

    @pytest.fixture
    def mock_answers(self):
        return [_make_answer(i, section_code="SEC1", confidence=0.85) for i in range(2)]

    @patch("app.api.routes.answers.get_db")
    @patch("app.api.deps.get_current_active_user")
    @patch("app.exports.answers.AnswerExporter.generate_pdf_report")
    def test_export_session_answers_pdf(
        self,
        mock_pdf_export,
        mock_auth,
        mock_db_dep,
        client,
        mock_db,
        mock_user,
        mock_session,
        mock_answers,
    ):
        """Test PDF export endpoint"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_db_dep.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = mock_session
        mock_db.query.return_value.join.return_value.join.return_value.filter.return_value.order_by.return_value.all.return_value = mock_answers

        # Mock PDF response
        mock_pdf_response = MagicMock()
        mock_pdf_response.media_type = "application/pdf"
        mock_pdf_response.body = b"PDF content"
        mock_pdf_export.return_value = mock_pdf_response

        # Make request
        response = client.get("/answers/session/1/export?format=pdf")

        # Assertions
        assert response.status_code == 200
        mock_pdf_export.assert_called_once_with(mock_session, mock_answers)

    @patch("app.api.routes.answers.get_db")
    @patch("app.api.deps.get_current_active_user")
    @patch("app.exports.answers.AnswerExporter.generate_excel_report")
    def test_export_session_answers_excel(
        self,
        mock_excel_export,
        mock_auth,
        mock_db_dep,
        client,
        mock_db,
        mock_user,
        mock_session,
        mock_answers,
    ):
        """Test Excel export endpoint"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_db_dep.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = mock_session
        mock_db.query.return_value.join.return_value.join.return_value.filter.return_value.order_by.return_value.all.return_value = mock_answers

        # Mock Excel response
        mock_excel_response = MagicMock()
        mock_excel_response.media_type = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        mock_excel_response.body = b"Excel content"
        mock_excel_export.return_value = mock_excel_response

        # Make request
        response = client.get("/answers/session/1/export?format=excel")

        # Assertions
        assert response.status_code == 200
        mock_excel_export.assert_called_once_with(mock_session, mock_answers)

    @patch("app.api.routes.answers.get_db")
    @patch("app.api.deps.get_current_active_user")
    def test_export_session_not_found(self, mock_auth, mock_db_dep, client, mock_db, mock_user):
        """Test export with non-existent session"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_db_dep.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Make request
        response = client.get("/answers/session/999/export?format=pdf")

        # Assertions
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @patch("app.api.routes.answers.get_db")
    @patch("app.api.deps.get_current_active_user")
    def test_export_no_answers(
        self, mock_auth, mock_db_dep, client, mock_db, mock_user, mock_session
    ):
        """Test export with no answers"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_db_dep.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = mock_session
        mock_db.query.return_value.join.return_value.join.return_value.filter.return_value.order_by.return_value.all.return_value = []

        # Make request
        response = client.get("/answers/session/1/export?format=pdf")

        # Assertions
        assert response.status_code == 404
        assert "No answers found" in response.json()["detail"]

    @patch("app.api.routes.answers.get_db")
    @patch("app.api.deps.get_current_active_user")
    def test_export_invalid_format(
        self, mock_auth, mock_db_dep, client, mock_db, mock_user, mock_session, mock_answers
    ):
        """Test export with invalid format"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_db_dep.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = mock_session
        mock_db.query.return_value.join.return_value.join.return_value.filter.return_value.order_by.return_value.all.return_value = mock_answers

        # Make request
        response = client.get("/answers/session/1/export?format=invalid")

        # Assertions
        assert response.status_code == 400
        assert "Format must be 'pdf' or 'excel'" in response.json()["detail"]


class TestAnswerAPICompatibility:
    """Test that answer API still works after export extraction"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def mock_db(self):
        return MagicMock(spec=Session)

    @pytest.fixture
    def mock_user(self):
        return User(id=1, email="test@example.com", username="testuser", role="user")

    @patch("app.api.routes.answers.get_db")
    @patch("app.api.deps.get_current_active_user")
    def test_answer_list_endpoint_still_works(
        self, mock_auth, mock_db_dep, client, mock_db, mock_user
    ):
        """Test that main answer list endpoint is unaffected by export extraction"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_db_dep.return_value = mock_db

        # Mock query chain for pagination
        mock_query = MagicMock()
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        mock_db.query.return_value = mock_query

        # Make request
        response = client.get("/answers/all")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "answers" in data
        assert "pagination" in data
        assert data["answers"] == []
        assert data["pagination"]["total_items"] == 0

    @patch("app.api.routes.answers.get_db")
    @patch("app.api.deps.get_current_active_user")
    def test_answer_stats_endpoint_still_works(
        self, mock_auth, mock_db_dep, client, mock_db, mock_user
    ):
        """Test that answer stats endpoint is unaffected"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_db_dep.return_value = mock_db

        # Mock various count queries
        mock_db.query.return_value.filter.return_value.count.return_value = 10
        mock_db.query.return_value.join.return_value.filter.return_value.count.return_value = 5

        # Make request
        response = client.get("/answers/stats")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "total_answers" in data
        assert "status_counts" in data
        assert "recent_activity" in data


if __name__ == "__main__":
    pytest.main([__file__])
