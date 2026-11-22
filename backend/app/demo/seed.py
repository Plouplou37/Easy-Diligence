"""The demo: a made-up due diligence, stored as a finished run leaves it.

`make demo` (the seed-demo command of app/cli.py) loads it into the running
application, so that every screen can be explored without an OpenAI key and
without any call to OpenAI. It writes:

- the questionnaire, built from questionnaire.json (a copy of
  examples/example_questionnaire.json) the way the import builds one;
- the fund under review;
- a session on that fund, owned by a user, with one run in status `generated`;
- one answer per question, with its sources and its history, as the engine
  stores them (engine/processor.py), most of them approved by the owner;
- the section summaries and the synthesis, as the summarizer stores them.

The texts are in data.json. There is no vector store and no raw OpenAI
response (dd_responses): both come from OpenAI.

One transaction. The demo is recognised by its session code. A reset deletes
that session and everything under it, then its questionnaire and its fund
unless something else uses them, and loads the demo again.
"""

import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from importlib import resources
from typing import Any

from sqlalchemy.orm import Session
from sqlmodel import col

from app.core.exceptions import ConflictError, InvalidRequestError, NotFoundError
from app.engine.answers import new_answer
from app.engine.openai_client import CONSULTED_LABEL
from app.engine.processor import INITIAL_ANSWER_REASON, regeneration_reason
from app.models.answer import AnswerStatus, DDAnswer
from app.models.answer_history import DDAnswerHistory
from app.models.base import stored_id
from app.models.company import Company, CompanyCreate
from app.models.dd_types import DEFAULT_DD_TYPE_ICON, DDType
from app.models.execution import DDExecution, ExecutionStatus
from app.models.questions import DDQuestion, DDSection
from app.models.session import DDSession, SessionDDType
from app.models.summary import DDSummary
from app.models.user import User
from app.models.vector_store import SessionVectorStore
from app.services.dd_types import add_structure
from app.services.file_parser import DDTypeFileParser

logger = logging.getLogger(__name__)

QUESTIONNAIRE_FILE = "questionnaire.json"
DATA_FILE = "data.json"

# A markdown link, the way the model writes a web citation:
# ([example.com](https://example.com/...)).
_LINK = re.compile(r"\[[^\]]+\]\((https?://[^)\s]+)\)")


def read_file(name: str) -> bytes:
    """A file of the demo's package data."""
    return resources.files("app.demo").joinpath(name).read_bytes()


def demo_data() -> dict[str, Any]:
    """The demo's texts and settings (data.json)."""
    data: dict[str, Any] = json.loads(read_file(DATA_FILE).decode("utf-8"))
    return data


# --- What the command reports -------------------------------------------------------


@dataclass
class DemoResult:
    """What seed_demo did."""

    session_code: str
    owner_email: str | None
    # False: the demo was there already, and nothing was written.
    loaded: bool
    session_name: str = ""
    questionnaire: str = ""
    fund: str = ""
    sections: int = 0
    questions: int = 0
    answers: int = 0
    versions: int = 0  # rows of the answers' history
    summaries: int = 0
    removed: list[str] = field(default_factory=list)  # deleted by the reset
    kept: list[str] = field(default_factory=list)  # left by the reset, and used again

    @property
    def path(self) -> str:
        """Where the session opens in the interface."""
        return f"/session/{self.session_code}"

    def lines(self) -> list[str]:
        """The report the command prints."""
        if not self.loaded:
            return [
                f"The demo is already loaded (owner: {self.owner_email or 'unknown'}). "
                f"Open {self.path}",
                "To load it again from scratch: run the command with --reset (make demo reset=1).",
            ]
        lines = []
        if self.removed:
            lines.append("Removed: " + ", ".join(self.removed) + ".")
        if self.kept:
            lines.append(
                "Kept, as another session uses it, and used again: " + ", ".join(self.kept) + "."
            )
        return [
            *lines,
            f"Demo loaded, owned by {self.owner_email}:",
            f"  questionnaire: {self.questionnaire} "
            f"({self.sections} sections, {self.questions} questions)",
            f"  fund: {self.fund}",
            f"  session: {self.session_name}, with {self.answers} answers "
            f"({self.versions} versions) and {self.summaries} summaries",
            f"Open it at {self.path}",
        ]


# --- Loading --------------------------------------------------------------------------


@dataclass(frozen=True)
class _Timeline:
    """When each step happened, so that the dates read like a review: the
    session created and run two days ago, one answer regenerated the next day,
    then the summaries, and the review two hours ago."""

    now: datetime

    @property
    def created(self) -> datetime:
        return self.now - timedelta(days=2)

    @property
    def run_started(self) -> datetime:
        return self.created + timedelta(minutes=5)

    @property
    def regenerated(self) -> datetime:
        return self.created + timedelta(days=1)

    @property
    def summarised(self) -> datetime:
        return self.regenerated + timedelta(minutes=10)

    @property
    def reviewed(self) -> datetime:
        return self.now - timedelta(hours=2)


@dataclass
class _Removal:
    """What the reset did, and what it kept for the demo to use again."""

    removed: list[str] = field(default_factory=list)
    kept: list[str] = field(default_factory=list)
    company: Company | None = None
    dd_type: DDType | None = None


def seed_demo(db: Session, *, owner_email: str | None = None, reset: bool = False) -> DemoResult:
    """Load the demo, in one transaction: nothing is written if anything fails.

    When it is loaded already, nothing is written, unless `reset`, which
    removes it first (_remove). The owner is the user with `owner_email`, or
    else the first active admin.
    """
    data = demo_data()
    code = data["session"]["code"]
    try:
        existing = db.query(DDSession).filter(col(DDSession.session_code) == code).first()
        if existing is not None and not reset:
            creator = existing.creator
            return DemoResult(
                session_code=code,
                owner_email=creator.email if creator is not None else None,
                loaded=False,
            )
        owner = _owner(db, owner_email)
        removal = (
            _remove(db, existing, data["questionnaire"]["code"])
            if existing is not None
            else _Removal()
        )
        loaded = _load(db, data, owner, removal, _Timeline(datetime.now(UTC)))
        result = _result(db, loaded, owner, removal)
        db.commit()
    except Exception:
        db.rollback()
        raise
    logger.info("Demo loaded: session %s, owned by %s", code, result.owner_email)
    return result


def _owner(db: Session, email: str | None) -> User:
    """The user who owns the demo: the one named, or else the first active admin."""
    if email:
        address = email.strip().lower()
        user = db.query(User).filter(col(User.email) == address).first()
        if user is None:
            raise NotFoundError(f"No user has the email {address}.")
        if not user.is_active:
            raise InvalidRequestError(f"The account {address} is deactivated: name an active user.")
        return user
    admin = (
        db.query(User)
        .filter(col(User.role) == "admin", col(User.is_active).is_(True))
        .order_by(col(User.id))
        .first()
    )
    if admin is not None:
        return admin
    if db.query(User).first() is None:
        raise NotFoundError(
            "There is no user yet. Create the first administrator "
            '(make admin email=you@example.com name="Full Name"), then run this command again.'
        )
    raise NotFoundError(
        "There is no active administrator. Name the demo's owner with --owner "
        "(make demo owner=you@example.com)."
    )


def _remove(db: Session, session: DDSession, questionnaire_code: str) -> _Removal:
    """Delete the demo session and everything under it (its run, answers,
    history and summaries, by cascade), then its fund and its questionnaire,
    unless another session uses them: those stay, and the demo uses them again.
    Nothing else is touched."""
    company = session.company
    dd_type = next(
        (
            link.dd_type
            for link in session.dd_type_links
            if link.dd_type is not None and link.dd_type.code == questionnaire_code
        ),
        None,
    )
    removal = _Removal(removed=[f"the session {session.session_code}"])
    db.delete(session)
    db.flush()

    if company is not None:
        if db.query(DDSession).filter(col(DDSession.company_id) == company.id).first() is None:
            db.delete(company)
            removal.removed.append(f"the fund {company.name}")
        else:
            removal.company = company
            removal.kept.append(f"the fund {company.name}")
    if dd_type is not None:
        if _in_use(db, dd_type):
            removal.dd_type = dd_type
            removal.kept.append(f"the questionnaire {dd_type.code}")
        else:
            db.delete(dd_type)
            removal.removed.append(f"the questionnaire {dd_type.code}")
    db.flush()
    return removal


def _in_use(db: Session, dd_type: DDType) -> bool:
    """Whether a session relies on the questionnaire (the demo's is deleted by now)."""
    dd_type_id = stored_id(dd_type)
    return (
        db.query(SessionDDType).filter(col(SessionDDType.dd_type_id) == dd_type_id).first()
        is not None
        or db.query(DDExecution).filter(col(DDExecution.dd_type_id) == dd_type_id).first()
        is not None
        or db.query(SessionVectorStore)
        .filter(col(SessionVectorStore.dd_type_id) == dd_type_id)
        .first()
        is not None
    )


@dataclass(frozen=True)
class _Loaded:
    session: DDSession
    dd_type: DDType
    company: Company


def _load(
    db: Session, data: dict[str, Any], owner: User, removal: _Removal, timeline: _Timeline
) -> _Loaded:
    """The questionnaire and the fund (unless the reset kept them), then the
    session, its run, its answers and its summaries. Flushed, not committed."""
    dd_type = (
        removal.dd_type
        if removal.dd_type is not None
        else _questionnaire(db, data["questionnaire"], owner, timeline)
    )
    company = (
        removal.company if removal.company is not None else _fund(db, data["fund"], owner, timeline)
    )

    meta = data["session"]
    session = DDSession(
        session_code=meta["code"],
        company_id=stored_id(company),
        name=meta["name"],
        description=meta["description"],
        created_by=stored_id(owner),
        assigned_to=stored_id(owner),
        created_at=timeline.created,
    )
    db.add(session)
    db.flush()
    db.add(SessionDDType(session_id=stored_id(session), dd_type_id=stored_id(dd_type), position=0))

    # A finished run: its time counted, no stretch going on.
    execution = DDExecution(
        session_id=stored_id(session),
        dd_type_id=stored_id(dd_type),
        status=ExecutionStatus.GENERATED,
        conversation_id=str(uuid.uuid4()),
        run_seconds=meta["run_seconds"],
        running_since=None,
        created_at=timeline.run_started,
    )
    db.add(execution)
    db.flush()

    _answers(db, data, execution, dd_type, owner, timeline)
    _summaries(db, data["summaries"], session, dd_type, timeline)
    db.flush()
    return _Loaded(session=session, dd_type=dd_type, company=company)


def _questionnaire(db: Session, meta: dict[str, Any], owner: User, timeline: _Timeline) -> DDType:
    """The questionnaire, built as the import builds one (services/dd_types.py),
    owned by the demo's owner. Never validated: validation cannot be undone."""
    if db.query(DDType).filter(col(DDType.code) == meta["code"]).first() is not None:
        raise ConflictError(
            f"A questionnaire with the code {meta['code']} already exists, and the demo did "
            "not create it. Change its code, then run this command again."
        )
    sections = DDTypeFileParser().parse_file(read_file(QUESTIONNAIRE_FILE), QUESTIONNAIRE_FILE)
    dd_type = DDType(
        code=meta["code"],
        name=meta["name"],
        description=meta["description"],
        icon=DEFAULT_DD_TYPE_ICON,
        order_index=0,
        is_active=True,
        is_system=False,
        created_by=stored_id(owner),
        created_at=timeline.created,
    )
    db.add(dd_type)
    db.flush()
    add_structure(db, dd_type, sections)
    return dd_type


def _fund(db: Session, fields: dict[str, Any], owner: User, timeline: _Timeline) -> Company:
    """The fund under review, as the company form creates it."""
    company = Company(
        **CompanyCreate.model_validate(fields).model_dump(),
        created_by=stored_id(owner),
        created_at=timeline.created,
    )
    db.add(company)
    db.flush()
    return company


def _answer_text(version: dict[str, Any]) -> str:
    """The answer as the model ends it: a last line names the documents it relied on."""
    documents = "; ".join(version["documents"]) or "none"
    return f"{version['text']}\n\n{CONSULTED_LABEL} {documents}"


def _sources(text: str, documents: list[str], data: dict[str, Any]) -> dict[str, Any]:
    """The sources as the engine stores them (OpenAIProcessor.process_question):
    one web source per citation in the text, then the documents named on its
    last line."""
    web = [
        {
            "type": "web_search",
            "url": match.group(1),
            "title": data["web_pages"][match.group(1)],
            "start_index": match.start(),
            "end_index": match.end(),
        }
        for match in _LINK.finditer(text)
    ]
    files = [
        {
            "type": "file_search",
            "file_id": data["documents"][name],
            "filename": name,
            "index": None,
        }
        for name in documents
    ]
    return {"files": files, "web": web, "total_count": len(files) + len(web)}


def _answers(
    db: Session,
    data: dict[str, Any],
    execution: DDExecution,
    dd_type: DDType,
    owner: User,
    timeline: _Timeline,
) -> None:
    """One answer per question, with a history row per version: the first one
    the AI's, as the run writes it, the next ones regenerations."""
    questions = {
        question.question_code: question
        for question in db.query(DDQuestion)
        .join(DDSection, col(DDQuestion.section_id) == col(DDSection.id))
        .filter(col(DDSection.dd_type_id) == dd_type.id)
    }
    entries = data["answers"]
    run_seconds = data["session"]["run_seconds"]
    for rank, entry in enumerate(entries):
        question = questions.get(entry["question"])
        if question is None:
            raise ConflictError(
                f"The questionnaire {dd_type.code} no longer has the question "
                f"{entry['question']}: the demo cannot be loaded on it again."
            )
        # The run answers the questions in turn, over its whole time.
        answered_at = timeline.run_started + timedelta(
            seconds=run_seconds * (rank + 1) / len(entries)
        )
        versions = entry["versions"]
        texts = [_answer_text(version) for version in versions]
        sources = [
            _sources(text, version["documents"], data)
            for text, version in zip(texts, versions, strict=True)
        ]
        status = AnswerStatus(entry["status"])
        regenerated = len(versions) > 1

        # A regeneration leaves the answer to review, as the AI's. Any other
        # status was set by the reviewer, who is then its last editor.
        edited_by: int | None
        if regenerated and status == AnswerStatus.NEEDS_REVIEW:
            edited_by, edited_at = None, timeline.regenerated
        else:
            edited_by, edited_at = stored_id(owner), timeline.reviewed + timedelta(minutes=rank)

        answer = new_answer(
            execution,
            question,
            answer_text=texts[-1],
            sources=sources[-1],
            tokens_used=versions[-1]["tokens_used"],
            status=status,
            retry_count=entry.get("retries", 0),
            version=len(versions),
            edited_by=edited_by,
            edited_at=edited_at,
            created_at=answered_at,
        )
        db.add(answer)
        db.flush()
        for number, (version, text, version_sources) in enumerate(
            zip(versions, texts, sources, strict=True), start=1
        ):
            first = number == 1
            db.add(
                DDAnswerHistory(
                    answer_id=stored_id(answer),
                    version=number,
                    content=text,
                    sources=version_sources,
                    edited_by=None,  # NULL: written by the AI
                    edit_reason=(
                        INITIAL_ANSWER_REASON
                        if first
                        else regeneration_reason(version.get("instruction"), guided=False)
                    ),
                    created_at=(
                        answered_at
                        if first
                        else timeline.regenerated + timedelta(minutes=number - 2)
                    ),
                )
            )


def _summaries(
    db: Session,
    summaries: dict[str, Any],
    session: DDSession,
    dd_type: DDType,
    timeline: _Timeline,
) -> None:
    """The section summaries, then the synthesis (the row without a section),
    in the order the summarizer writes them."""
    sections = {
        section.section_code: section
        for section in db.query(DDSection).filter(col(DDSection.dd_type_id) == dd_type.id)
    }
    for code, text in summaries["sections"].items():
        section = sections.get(code)
        if section is None:
            raise ConflictError(
                f"The questionnaire {dd_type.code} no longer has the section {code}: "
                "the demo cannot be loaded on it again."
            )
        db.add(
            DDSummary(
                session_id=stored_id(session),
                dd_type_id=stored_id(dd_type),
                section_id=stored_id(section),
                summary_text=text,
                generated_at=timeline.summarised,
            )
        )
    db.add(
        DDSummary(
            session_id=stored_id(session),
            dd_type_id=stored_id(dd_type),
            section_id=None,
            summary_text=summaries["synthesis"],
            generated_at=timeline.summarised + timedelta(minutes=1),
        )
    )


def _result(db: Session, loaded: _Loaded, owner: User, removal: _Removal) -> DemoResult:
    """What was loaded, counted in the database."""
    session_id, dd_type_id = stored_id(loaded.session), stored_id(loaded.dd_type)
    return DemoResult(
        session_code=loaded.session.session_code or "",
        owner_email=owner.email,
        loaded=True,
        session_name=loaded.session.name,
        questionnaire=f"{loaded.dd_type.code}, {loaded.dd_type.name}",
        fund=loaded.company.name,
        sections=db.query(DDSection).filter(col(DDSection.dd_type_id) == dd_type_id).count(),
        questions=db.query(DDQuestion)
        .join(DDSection, col(DDQuestion.section_id) == col(DDSection.id))
        .filter(col(DDSection.dd_type_id) == dd_type_id)
        .count(),
        answers=db.query(DDAnswer).filter(col(DDAnswer.session_id) == session_id).count(),
        versions=db.query(DDAnswerHistory)
        .join(DDAnswer, col(DDAnswerHistory.answer_id) == col(DDAnswer.id))
        .filter(col(DDAnswer.session_id) == session_id)
        .count(),
        summaries=db.query(DDSummary).filter(col(DDSummary.session_id) == session_id).count(),
        removed=removal.removed,
        kept=removal.kept,
    )
