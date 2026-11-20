"""Editing the structure of a DD type: its sections and questions.

Only the owner of a DD type (or an admin) may change it, and only until it is
validated: validation freezes the structure, so that answers keep matching the
questions they were written for. A new section takes the next letter, a new
question the next code of its section (services/question_codes.py).

Codes are unique in their DD type (sections) or section (questions), and the
database holds the rule: a code taken meanwhile by another request is a
conflict too, not an error.
"""

from collections.abc import Callable
from typing import Any

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlmodel import col

from app.core.exceptions import ConflictError, InvalidRequestError, NotFoundError
from app.models.base import stored_id
from app.models.dd_types import DDType
from app.models.questions import (
    DDQuestion,
    DDSection,
    QuestionCreate,
    QuestionUpdate,
    SectionCreate,
    SectionUpdate,
)
from app.models.user import User
from app.services.authz import assert_dd_type_ownership, assert_dd_type_view
from app.services.dd_types import get_dd_type_by_code, get_section_in
from app.services.question_codes import next_question_code, next_section_code


def _assert_editable(dd_type: DDType, user: User) -> None:
    """The user may change this DD type's structure: it is visible to them,
    theirs (or they are an admin), and not validated yet."""
    assert_dd_type_view(dd_type, user)
    assert_dd_type_ownership(dd_type, user)
    if dd_type.is_validated:
        raise InvalidRequestError(
            f"DD type '{dd_type.name}' has been validated and is now immutable. "
            "Cannot modify validated DD types to maintain data integrity. "
            "Please create a new DD type if you need to make changes."
        )


def _editable_dd_type(db: Session, code: str, user: User) -> DDType:
    dd_type = get_dd_type_by_code(db, code, user)
    _assert_editable(dd_type, user)
    return dd_type


def _editable_section(db: Session, section_id: int, user: User) -> DDSection:
    section = db.get(DDSection, section_id)
    if section is None or section.dd_type_obj is None:
        raise NotFoundError("Section not found")
    _assert_editable(section.dd_type_obj, user)
    return section


def _editable_question(db: Session, question_id: int, user: User) -> DDQuestion:
    question = db.get(DDQuestion, question_id)
    if question is None:
        raise NotFoundError("Question not found")
    _editable_section(db, question.section_id, user)
    return question


SECTION_CODE_TAKEN = "Section code already exists in this DD type"
QUESTION_CODE_TAKEN = "Question code already exists in this section"


def _section_code_taken(db: Session, dd_type_id: int, code: str) -> bool:
    return (
        db.query(DDSection).filter_by(dd_type_id=dd_type_id, section_code=code).first() is not None
    )


def _question_code_taken(db: Session, section_id: int, code: str) -> bool:
    return (
        db.query(DDQuestion).filter_by(section_id=section_id, question_code=code).first()
        is not None
    )


def _commit(db: Session, row: Any, code_taken: Callable[[], bool], message: str) -> None:
    """Commit; a code taken meanwhile by another request is a ConflictError.
    Any other integrity error is left to propagate."""
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if code_taken():
            raise ConflictError(message) from None
        raise
    db.refresh(row)


# --- Sections ---------------------------------------------------------------------


def create_section(db: Session, code: str, data: SectionCreate, user: User) -> DDSection:
    """A new section, after the last one unless an order is given, with the next letter."""
    dd_type = _editable_dd_type(db, code, user)
    dd_type_id = stored_id(dd_type)
    existing = [s.section_code for s in db.query(DDSection).filter_by(dd_type_id=dd_type_id)]

    order_index = data.order_index
    if order_index is None:
        last = (
            db.query(func.max(col(DDSection.order_index)))
            .filter(col(DDSection.dd_type_id) == dd_type_id)
            .scalar()
        )
        # A first section is number 0 (this was `last or -1`, which put a
        # section after one at 0 at 0 again).
        order_index = 0 if last is None else last + 1

    section_code = next_section_code(existing)
    section = DDSection(
        dd_type_id=dd_type_id,
        section_code=section_code,
        title=data.title,
        description=data.description,
        order_index=order_index,
    )
    db.add(section)
    _commit(
        db,
        section,
        lambda: _section_code_taken(db, dd_type_id, section_code),
        # Only a section added at the same time can have taken the letter.
        "Another section was added at the same time: please try again.",
    )
    return section


def update_section(db: Session, section_id: int, data: SectionUpdate, user: User) -> DDSection:
    section = _editable_section(db, section_id, user)
    dd_type_id = section.dd_type_id
    changes = data.model_dump(exclude_unset=True)
    new_code = changes.get("section_code")
    if new_code == section.section_code:
        new_code = None
    if new_code and _section_code_taken(db, dd_type_id, new_code):
        raise ConflictError(SECTION_CODE_TAKEN)
    for field, value in changes.items():
        setattr(section, field, value)
    _commit(
        db,
        section,
        lambda: new_code is not None and _section_code_taken(db, dd_type_id, new_code),
        SECTION_CODE_TAKEN,
    )
    return section


def delete_section(db: Session, section_id: int, user: User) -> None:
    """Delete a section and its questions."""
    section = _editable_section(db, section_id, user)
    db.delete(section)
    db.commit()


def move_section(db: Session, section_id: int, new_order: int, user: User) -> DDSection:
    """Swap places with the section at `new_order`, if there is one."""
    section = _editable_section(db, section_id, user)
    target = (
        db.query(DDSection).filter_by(dd_type_id=section.dd_type_id, order_index=new_order).first()
    )
    if target is not None:
        section.order_index, target.order_index = target.order_index, section.order_index
    db.commit()
    db.refresh(section)
    return section


# --- Questions --------------------------------------------------------------------


def section_questions(db: Session, code: str, section_id: int, user: User) -> list[DDQuestion]:
    """The questions of a section of a DD type the user may see, in order."""
    section = get_section_in(db, get_dd_type_by_code(db, code, user), section_id)
    return list(section.questions)


def create_question(
    db: Session, code: str, section_id: int, data: QuestionCreate, user: User
) -> DDQuestion:
    """A new question in a section; without a code, it takes the next one (A.07)."""
    section = get_section_in(db, _editable_dd_type(db, code, user), section_id)
    existing = [q.question_code for q in section.questions]
    question_code = data.question_code or next_question_code(section.section_code, existing)
    if question_code in existing:
        raise ConflictError(QUESTION_CODE_TAKEN)

    section_id = stored_id(section)
    question = DDQuestion(
        section_id=section_id,
        question_code=question_code,
        question_text=data.question_text,
        context_prompt=data.context_prompt,
        order_index=data.order_index,
    )
    db.add(question)
    _commit(
        db,
        question,
        lambda: _question_code_taken(db, section_id, question_code),
        QUESTION_CODE_TAKEN,
    )
    return question


def update_question(db: Session, question_id: int, data: QuestionUpdate, user: User) -> DDQuestion:
    question = _editable_question(db, question_id, user)
    section_id = question.section_id
    changes = data.model_dump(exclude_unset=True)
    new_code = changes.get("question_code")
    if new_code == question.question_code:
        new_code = None
    if new_code and _question_code_taken(db, section_id, new_code):
        raise ConflictError(QUESTION_CODE_TAKEN)
    for field, value in changes.items():
        setattr(question, field, value)
    _commit(
        db,
        question,
        lambda: new_code is not None and _question_code_taken(db, section_id, new_code),
        QUESTION_CODE_TAKEN,
    )
    return question


def delete_question(db: Session, question_id: int, user: User) -> None:
    question = _editable_question(db, question_id, user)
    db.delete(question)
    db.commit()


def move_question(db: Session, question_id: int, new_order: int, user: User) -> DDQuestion:
    """Swap places with the question at `new_order` in the section, if there is one."""
    question = _editable_question(db, question_id, user)
    target = (
        db.query(DDQuestion)
        .filter_by(section_id=question.section_id, order_index=new_order)
        .first()
    )
    if target is not None:
        question.order_index, target.order_index = target.order_index, question.order_index
    db.commit()
    db.refresh(question)
    return question
