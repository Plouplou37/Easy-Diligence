"""DD types (questionnaires): lookup, listing, creation (blank or from a file),
changes, activation, validation, deletion.

A validated DD type is frozen: its sections and questions can no longer change
(services/questions.py). Validation is irreversible.
"""

from typing import Any

from sqlalchemy.orm import Session, joinedload
from sqlmodel import col

from app.core.exceptions import (
    ConflictError,
    InvalidRequestError,
    NotFoundError,
    PermissionDeniedError,
)
from app.models.base import relation, stored_id
from app.models.dd_types import DEFAULT_DD_TYPE_ICON, DDType, DDTypeCreate, DDTypeUpdate
from app.models.questions import DDQuestion, DDSection
from app.models.user import User
from app.services.authz import (
    assert_dd_type_ownership,
    assert_dd_type_view,
    filter_dd_types_for_user,
)
from app.services.file_parser import DDTypeFileParser, FileParsingError


def get_dd_type_by_code(db: Session, code: str, user: User | None = None) -> DDType:
    """The DD type with this code. With a user, one they may see: a private
    type of someone else is reported missing, like an unknown code."""
    dd_type = db.query(DDType).filter(col(DDType.code) == code).first()
    if dd_type is None:
        raise NotFoundError(f"DD type with code '{code}' not found")
    if user is not None:
        assert_dd_type_view(dd_type, user)
    return dd_type


def get_owned_dd_type(db: Session, code: str, user: User) -> DDType:
    """A DD type the user may change: visible to them (404 otherwise), and
    theirs or they are an admin (403 otherwise)."""
    dd_type = get_dd_type_by_code(db, code, user)
    assert_dd_type_ownership(dd_type, user)
    return dd_type


def list_dd_types(
    db: Session,
    user: User,
    *,
    active_only: bool = True,
    with_questions: bool = False,
    skip: int = 0,
    limit: int | None = None,
) -> list[DDType]:
    """The DD types the user may see (theirs and the shared ones)."""
    query = db.query(DDType)
    if with_questions:
        query = query.options(
            joinedload(relation(DDType.sections)).joinedload(relation(DDSection.questions))
        )
    if active_only:
        query = query.filter(col(DDType.is_active).is_(True))
    query = filter_dd_types_for_user(query, user).order_by(
        col(DDType.order_index), col(DDType.name)
    )
    if skip:
        query = query.offset(skip)
    if limit is not None:
        query = query.limit(limit)
    return query.all()


def _assert_code_free(db: Session, code: str) -> None:
    if db.query(DDType).filter(col(DDType.code) == code).first() is not None:
        raise InvalidRequestError("DD type code already exists")


def create_dd_type(db: Session, data: DDTypeCreate, user: User) -> DDType:
    """An empty DD type, owned by the user."""
    _assert_code_free(db, data.code)
    dd_type = DDType(
        code=data.code,
        name=data.name,
        description=data.description,
        icon=data.icon,
        order_index=data.order_index,
        is_active=True,
        is_system=False,
        created_by=stored_id(user),
    )
    db.add(dd_type)
    db.commit()
    db.refresh(dd_type)
    return dd_type


def import_dd_type(
    db: Session,
    user: User,
    *,
    code: str,
    name: str,
    description: str | None,
    icon: str | None,
    content: bytes,
    filename: str,
) -> DDType:
    """A DD type built from a questionnaire file (Excel, CSV or JSON)."""
    _assert_code_free(db, code)
    try:
        sections = DDTypeFileParser().parse_file(content, filename)
    except FileParsingError as error:
        # The parser's messages describe what is wrong with the file.
        raise InvalidRequestError(f"File parsing error: {error}") from error

    dd_type = DDType(
        code=code,
        name=name,
        description=description,
        icon=icon or DEFAULT_DD_TYPE_ICON,
        order_index=0,
        is_active=True,
        is_system=False,
        created_by=stored_id(user),
    )
    db.add(dd_type)
    db.flush()
    for section_data in sections:
        section = DDSection(
            dd_type_id=stored_id(dd_type),
            section_code=section_data["section_code"],
            title=section_data["title"],
            # Sent to the model with the section heading: empty is better than
            # a placeholder that restates the title.
            description=section_data.get("description"),
            order_index=section_data["order_index"],
        )
        db.add(section)
        db.flush()
        for question_data in section_data["questions"]:
            db.add(
                DDQuestion(
                    section_id=stored_id(section),
                    question_code=question_data["question_code"],
                    question_text=question_data["question_text"],
                    context_prompt=question_data.get("context_prompt"),
                    order_index=question_data["order_index"],
                )
            )
    db.commit()
    db.refresh(dd_type)
    return dd_type


def update_dd_type(db: Session, dd_type: DDType, data: DDTypeUpdate) -> DDType:
    """Change a DD type's name, code, description, icon, order or activity."""
    changes: dict[str, Any] = data.model_dump(exclude_unset=True)
    new_code = changes.get("code")
    if new_code and new_code != dd_type.code:
        if dd_type.is_system:
            raise PermissionDeniedError("Cannot change code of system DD type")
        _assert_code_free(db, new_code)
    for field, value in changes.items():
        setattr(dd_type, field, value)
    db.commit()
    db.refresh(dd_type)
    return dd_type


def set_active(db: Session, dd_type: DDType, active: bool) -> DDType:
    """Offer the DD type for new sessions, or stop offering it."""
    dd_type.is_active = active
    db.commit()
    db.refresh(dd_type)
    return dd_type


def validate_dd_type(db: Session, dd_type: DDType) -> DDType:
    """Freeze the DD type's structure. Irreversible."""
    if dd_type.is_validated:
        raise InvalidRequestError(f"DD type '{dd_type.name}' is already validated and locked")
    dd_type.is_validated = True
    db.commit()
    db.refresh(dd_type)
    return dd_type


def delete_dd_type(db: Session, dd_type: DDType) -> None:
    """Delete a DD type and its structure, unless it is a system type or has
    been run (deactivate it then)."""
    if dd_type.is_system:
        raise PermissionDeniedError("Cannot delete system DD type")
    if dd_type.executions:
        raise ConflictError("Cannot delete DD type that is in use. Set to inactive instead.")
    db.delete(dd_type)
    db.commit()


def get_with_questions(db: Session, code: str, user: User) -> DDType:
    """A DD type the user may see, with its sections and questions loaded."""
    dd_type = (
        db.query(DDType)
        .options(joinedload(relation(DDType.sections)).joinedload(relation(DDSection.questions)))
        .filter(col(DDType.code) == code)
        .first()
    )
    if dd_type is None:
        raise NotFoundError("DD type not found")
    assert_dd_type_view(dd_type, user)
    return dd_type


def get_section_in(db: Session, dd_type: DDType, section_id: int) -> DDSection:
    """A section of this DD type."""
    section = db.get(DDSection, section_id)
    if section is None or section.dd_type_id != dd_type.id:
        raise NotFoundError("Section not found")
    return section
