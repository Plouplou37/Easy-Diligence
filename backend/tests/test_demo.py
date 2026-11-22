"""The demo (app/demo, `make demo`): what it loads, that it loads once, that
--reset loads it again without touching anything else, and that its
questionnaire is the example one."""

import json
import re
from collections import Counter
from pathlib import Path

import pytest
from typer.testing import CliRunner

import app.cli as cli_module
from app.core.exceptions import ConflictError, InvalidRequestError, NotFoundError
from app.demo import seed
from app.demo.seed import QUESTIONNAIRE_FILE, demo_data, read_file, seed_demo
from app.engine.openai_client import CONSULTED_LABEL, documents_consulted
from app.engine.processor import INITIAL_ANSWER_REASON
from app.models.answer import AnswerStatus, DDAnswer
from app.models.answer_history import DDAnswerHistory
from app.models.company import Company
from app.models.dd_types import DDType
from app.models.execution import DDExecution, ExecutionStatus
from app.models.questions import DDQuestion, DDSection
from app.models.session import DDSession, SessionDDType
from app.models.summary import DDSummary

EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "example_questionnaire.json"
DATA = demo_data()
CODE = DATA["session"]["code"]
TABLES = (
    Company,
    DDType,
    DDSection,
    DDQuestion,
    DDSession,
    SessionDDType,
    DDExecution,
    DDAnswer,
    DDAnswerHistory,
    DDSummary,
)
NOTHING = {model.__name__: 0 for model in TABLES}


def counts(db):
    return {model.__name__: db.query(model).count() for model in TABLES}


def demo_session(db):
    return db.query(DDSession).filter(DDSession.session_code == CODE).one()


# --- The data ---------------------------------------------------------------------


def test_the_questionnaire_is_a_copy_of_the_example():
    """The backend image holds backend/ only: the demo keeps its own copy."""
    copy = json.loads(read_file(QUESTIONNAIRE_FILE).decode("utf-8"))
    assert copy == json.loads(EXAMPLE.read_text(encoding="utf-8"))


def test_the_data_holds_together():
    questionnaire = json.loads(read_file(QUESTIONNAIRE_FILE).decode("utf-8"))
    references = [question["ref"] for section in questionnaire for question in section["questions"]]
    assert [entry["question"] for entry in DATA["answers"]] == references
    assert list(DATA["summaries"]["sections"]) == list("ABCDEF")[: len(questionnaire)]
    assert all(url.startswith("https://example.com/") for url in DATA["web_pages"])

    for entry in DATA["answers"]:
        AnswerStatus(entry["status"])
        for number, version in enumerate(entry["versions"], start=1):
            assert set(version["documents"]) <= set(DATA["documents"])
            assert 9_000 <= version["tokens_used"] <= 14_000
            # Every version after the first is a regeneration, with its instruction.
            assert ("instruction" in version) == (number > 1)
            links = re.findall(r"\]\((https?://[^)\s]+)\)", version["text"])
            assert set(links) <= set(DATA["web_pages"])
            # The last line is the seed's, from the documents.
            assert CONSULTED_LABEL not in version["text"]


# --- What it loads ------------------------------------------------------------------


def test_the_demo_is_a_finished_due_diligence(db, admin):
    result = seed_demo(db)

    assert result.loaded
    assert result.path == f"/session/{CODE}"
    assert (result.sections, result.questions, result.answers) == (6, 18, 18)
    assert (result.versions, result.summaries) == (19, 7)

    session = demo_session(db)
    assert (session.created_by, session.assigned_to) == (admin.id, admin.id)
    assert session.name == "Example Asia Fund — annual review (demo)"
    fund = session.company
    assert (fund.name, fund.website_url) == ("Example Asia Fund", "https://example.com/asia-fund")
    assert fund.management_company_name == "Example Fund Management"
    assert fund.created_by == admin.id
    assert [link.dd_type.code for link in session.dd_type_links] == ["DEMO"]

    dd_type = db.query(DDType).filter(DDType.code == "DEMO").one()
    assert dd_type.name == "Example questionnaire (demo)"
    assert (dd_type.created_by, dd_type.is_active, dd_type.is_validated) == (admin.id, True, False)
    sections = dd_type.sections
    assert [section.section_code for section in sections] == list("ABCDEF")
    questions = [question for section in sections for question in section.questions]
    assert questions[0].question_code == "A.01" and questions[-1].question_code == "F.03"
    assert all(question.context_prompt for question in questions)

    execution = db.query(DDExecution).filter(DDExecution.session_id == session.id).one()
    assert execution.status == ExecutionStatus.GENERATED
    assert (execution.run_seconds, execution.running_since) == (270, None)
    assert execution.elapsed_seconds() == 270


def test_the_answers_are_stored_as_the_engine_stores_them(db, admin):
    seed_demo(db)
    session = demo_session(db)
    answers = db.query(DDAnswer).filter(DDAnswer.session_id == session.id).all()

    assert len(answers) == 18 and all(answer.is_current for answer in answers)
    assert Counter(answer.status for answer in answers) == {
        AnswerStatus.APPROVED: 15,
        AnswerStatus.NEEDS_REVIEW: 3,
    }
    search_results = [
        {"file_id": file_id, "filename": name} for name, file_id in DATA["documents"].items()
    ]
    for answer in answers:
        assert answer.question.question_code == answer.question_code
        assert answer.section_code == answer.question.section.section_code
        assert 9_000 <= answer.tokens_used <= 14_000
        last_line = answer.answer_text.splitlines()[-1]
        assert last_line.startswith(CONSULTED_LABEL)

        sources = answer.sources
        assert set(sources) == {"files", "web", "total_count"}
        assert sources["total_count"] == len(sources["files"]) + len(sources["web"])
        # The documents are those the engine would read on the last line.
        named = last_line.removeprefix(CONSULTED_LABEL).strip().split("; ")
        assert [source["filename"] for source in sources["files"]] == named
        rebuilt = documents_consulted(answer.answer_text, search_results)
        assert sorted(rebuilt, key=lambda s: s["filename"]) == sorted(
            sources["files"], key=lambda s: s["filename"]
        )
        for source in sources["web"]:
            assert set(source) == {"type", "url", "title", "start_index", "end_index"}
            assert source["type"] == "web_search"
            cited = answer.answer_text[source["start_index"] : source["end_index"]]
            assert cited.endswith(f"({source['url']})")

    # Approved by the owner, or regenerated by the AI and left to review.
    regenerated = [answer for answer in answers if answer.version == 2]
    assert len(regenerated) == 1
    assert regenerated[0].status == AnswerStatus.NEEDS_REVIEW
    assert regenerated[0].edited_by is None and regenerated[0].edited_at is not None
    approved = [answer for answer in answers if answer.status == AnswerStatus.APPROVED]
    assert all(answer.edited_by == admin.id for answer in approved)

    history = db.query(DDAnswerHistory).all()
    assert len(history) == 19
    assert Counter(row.answer_id for row in history)[regenerated[0].id] == 2
    first, second = sorted(regenerated[0].history, key=lambda row: row.version)
    assert first.edit_reason == INITIAL_ANSWER_REASON
    assert second.edit_reason.startswith("Regenerated by the AI — instruction: ")
    assert second.content == regenerated[0].answer_text
    assert second.sources == regenerated[0].sources
    assert all(row.edited_by is None for row in history)


def test_the_summaries_are_stored_as_the_summarizer_stores_them(db, admin):
    seed_demo(db)
    summaries = db.query(DDSummary).order_by(DDSummary.id).all()

    assert [summary.section.section_code for summary in summaries[:-1]] == list("ABCDEF")
    synthesis = summaries[-1]
    assert synthesis.section_id is None
    for heading in (
        "## Introduction",
        "## Key Points",
        "## Strengths",
        "## Risks and Points of Attention",
        "## Conclusion and Recommendation",
    ):
        assert heading in synthesis.summary_text
    assert "\n### " in synthesis.summary_text and "\n- " in synthesis.summary_text
    assert all(summary.edited_by is None for summary in summaries)


def test_the_owner_finds_it_in_the_application(db, client, admin, auth_headers):
    seed_demo(db)
    headers = auth_headers(admin)

    listing = client.get("/api/session/", headers=headers).json()
    assert [session["session_code"] for session in listing["sessions"]] == [CODE]

    (progress,) = client.get(f"/api/session/{CODE}/status", headers=headers).json()["progress"]
    assert progress["status"] == "completed"
    assert (progress["questions_completed"], progress["total_questions"]) == (18, 18)
    assert (progress["time_elapsed"], progress["answers_with_documents"]) == (270, 18)

    (row,) = client.get("/api/dashboard/sessions", headers=headers).json()["sessions"]
    (run,) = row["dd_types"]
    assert (run["approved"], run["to_review"], run["has_synthesis"]) == (15, 3, True)

    answers = client.get(f"/api/answers/session/{CODE}", headers=headers).json()["answers"]
    assert [answer["question_code"] for answer in answers] == [
        entry["question"] for entry in DATA["answers"]
    ]
    regenerated = next(answer for answer in answers if answer["version"] == 2)
    versions = client.get(f"/api/answers/{regenerated['id']}/history", headers=headers).json()
    assert versions["total_versions"] == 2

    summaries = client.get(f"/api/summaries/session/{CODE}", headers=headers).json()
    assert len(summaries) == 7


def test_the_report_exports(db, client, admin, auth_headers):
    seed_demo(db)
    response = client.get(f"/api/answers/session/{CODE}/export", headers=auth_headers(admin))
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


def test_an_analyst_can_own_it(db, client, admin, analyst, auth_headers):
    result = seed_demo(db, owner_email=f"  {analyst.email.upper()} ")
    assert result.owner_email == analyst.email

    headers = auth_headers(analyst)
    sessions = client.get("/api/session/", headers=headers).json()["sessions"]
    assert [session["session_code"] for session in sessions] == [CODE]
    dd_types = client.get("/api/dd-types/", headers=headers).json()
    assert "DEMO" in [dd_type["code"] for dd_type in dd_types]


# --- The owner ----------------------------------------------------------------------


def test_the_default_owner_is_the_first_active_administrator(db, make_user):
    make_user("admin", is_active=False)
    make_user("analyst")
    first = make_user("admin")
    make_user("admin")
    assert seed_demo(db).owner_email == first.email


def test_without_any_user(db):
    with pytest.raises(NotFoundError, match="make admin"):
        seed_demo(db)
    assert counts(db) == NOTHING


def test_without_an_administrator_the_owner_must_be_named(db, analyst):
    with pytest.raises(NotFoundError, match="--owner"):
        seed_demo(db)
    assert seed_demo(db, owner_email=analyst.email).loaded


def test_the_owner_must_be_an_active_user(db, admin, make_user):
    with pytest.raises(NotFoundError, match="nobody@example.com"):
        seed_demo(db, owner_email="nobody@example.com")
    inactive = make_user(is_active=False)
    with pytest.raises(InvalidRequestError, match="deactivated"):
        seed_demo(db, owner_email=inactive.email)
    assert counts(db) == NOTHING


# --- Once, and again with --reset ----------------------------------------------------


def test_a_second_run_writes_nothing(db, admin):
    seed_demo(db)
    before = counts(db)

    again = seed_demo(db)

    assert not again.loaded
    assert again.owner_email == admin.email
    assert "already loaded" in again.lines()[0]
    assert counts(db) == before


def test_reset_loads_it_again(db, admin):
    seed_demo(db)
    old_run = db.query(DDExecution).one().conversation_id
    # A reviewer's edit: the reset deletes it with the session.
    answer = db.query(DDAnswer).first()
    answer.answer_text = "Edited by the reviewer"
    db.commit()
    before = counts(db)

    result = seed_demo(db, reset=True)

    assert result.loaded
    assert result.removed == [
        f"the session {CODE}",
        "the fund Example Asia Fund",
        "the questionnaire DEMO",
    ]
    assert result.kept == []
    assert counts(db) == before
    # A new run (SQLite may give the new rows the ids of the old ones).
    assert db.query(DDExecution).one().conversation_id != old_run
    assert db.query(DDAnswer).filter(DDAnswer.answer_text == "Edited by the reviewer").count() == 0


def test_reset_without_a_demo_loads_it(db, admin):
    result = seed_demo(db, reset=True)
    assert result.loaded and result.removed == []
    assert counts(db)["DDAnswer"] == 18


def test_reset_keeps_what_another_session_uses(db, admin, make_dd_session):
    seed_demo(db)
    demo = demo_session(db)
    fund_id, dd_type_id = demo.company_id, demo.dd_type_links[0].dd_type_id
    other = make_dd_session(admin, company=demo.company)
    db.add(SessionDDType(session_id=other.id, dd_type_id=dd_type_id, position=0))
    db.commit()

    result = seed_demo(db, reset=True)

    assert result.removed == [f"the session {CODE}"]
    assert result.kept == ["the fund Example Asia Fund", "the questionnaire DEMO"]
    demo = demo_session(db)
    assert demo.company_id == fund_id
    assert [link.dd_type_id for link in demo.dd_type_links] == [dd_type_id]
    assert db.get(DDSession, other.id) is not None
    assert db.query(Company).count() == 1
    assert db.query(DDType).count() == 1
    assert db.query(DDAnswer).count() == 18


def test_reset_never_deletes_what_it_did_not_create(db, admin, make_company, make_dd_type):
    lookalike = make_company(admin)  # named "Example Asia Fund" too
    questionnaire = make_dd_type(admin)
    seed_demo(db)

    seed_demo(db, reset=True)

    assert db.get(Company, lookalike.id) is not None
    assert db.get(DDType, questionnaire.id) is not None
    assert db.query(Company).count() == 2


def test_a_questionnaire_coded_demo_is_left_alone(db, admin, make_dd_type):
    taken = make_dd_type(admin, code="DEMO")
    name = taken.name
    before = counts(db)

    with pytest.raises(ConflictError, match="DEMO"):
        seed_demo(db)

    assert counts(db) == before
    assert db.get(DDType, taken.id).name == name


def test_nothing_is_written_when_a_step_fails(db, admin, monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("the summaries could not be written")

    monkeypatch.setattr(seed, "_summaries", broken)
    with pytest.raises(RuntimeError):
        seed_demo(db)
    assert counts(db) == NOTHING


# --- The command ------------------------------------------------------------------------


def test_the_command(session_factory, admin, monkeypatch):
    monkeypatch.setattr(cli_module, "SessionLocal", session_factory)
    runner = CliRunner()

    first = runner.invoke(cli_module.cli, ["seed-demo"])
    assert first.exit_code == 0, first.output
    assert f"Demo loaded, owned by {admin.email}" in first.output
    assert f"Open it at /session/{CODE}" in first.output

    again = runner.invoke(cli_module.cli, ["seed-demo"])
    assert again.exit_code == 0, again.output
    assert "already loaded" in again.output

    reset = runner.invoke(cli_module.cli, ["seed-demo", "--reset", "--owner", admin.email])
    assert reset.exit_code == 0, reset.output
    assert f"Removed: the session {CODE}" in reset.output


def test_the_command_without_any_user(session_factory, monkeypatch):
    monkeypatch.setattr(cli_module, "SessionLocal", session_factory)
    result = CliRunner().invoke(cli_module.cli, ["seed-demo"])
    assert result.exit_code == 1
    assert "make admin" in result.stderr
