"""Model constraints and cascades, on a real (SQLite) database."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.answer import AnswerStatus, DDAnswer
from app.models.answer_history import DDAnswerHistory
from app.models.company import Company
from app.models.execution import DDExecution
from app.models.questions import DDQuestion
from app.models.session import DDSession
from app.models.user import User
from tests.conftest import PASSWORD_HASH


def test_user_defaults(db):
    user = User(email="model@example.com", username="model", password_hash=PASSWORD_HASH)
    db.add(user)
    db.commit()
    db.refresh(user)
    assert user.id is not None
    assert user.role == "analyst"
    assert user.is_active is True
    assert user.created_at is not None


def test_email_is_unique(db):
    db.add(User(email="unique@example.com", username="first", password_hash=PASSWORD_HASH))
    db.commit()
    db.add(User(email="unique@example.com", username="second", password_hash=PASSWORD_HASH))
    with pytest.raises(IntegrityError):
        db.commit()


def test_company_name_is_required(db):
    db.add(Company(name=None, website_url="https://example.com"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_company_timestamps_are_filled_by_the_database(db):
    company = Company(name="Example Asia Fund")
    db.add(company)
    db.commit()
    db.refresh(company)
    assert company.created_at is not None
    assert company.updated_at is not None


def test_deleting_a_session_deletes_its_answers_and_history(
    db, analyst, make_dd_type, make_dd_session
):
    dd_type = make_dd_type()
    session = make_dd_session(analyst)
    question = db.query(DDQuestion).first()
    execution = DDExecution(session_id=session.id, dd_type_id=dd_type.id, status="generated")
    db.add(execution)
    db.flush()
    answer = DDAnswer(
        session_id=session.id,
        execution_id=execution.id,
        section_code="S1",
        question_code=question.question_code,
        question_id=question.id,
        answer_text="An answer",
        status=AnswerStatus.COMPLETED,
    )
    db.add(answer)
    db.flush()
    db.add(DDAnswerHistory(answer_id=answer.id, version=1, content="An answer"))
    db.commit()

    db.delete(db.get(DDSession, session.id))
    db.commit()

    assert db.query(DDExecution).count() == 0
    assert db.query(DDAnswer).count() == 0
    assert db.query(DDAnswerHistory).count() == 0


def test_answer_status_is_checked(db, analyst, make_dd_session):
    session = make_dd_session(analyst)
    db.add(DDAnswer(session_id=session.id, section_code="S", question_code="Q", status="bogus"))
    with pytest.raises((IntegrityError, LookupError, ValueError)):
        db.commit()
