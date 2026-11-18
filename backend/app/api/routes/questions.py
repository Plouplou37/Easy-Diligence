"""The structure of the DD types: sections and questions, read and edited.

Editing is for the owner of a DD type (or an admin), until it is validated.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.questions import (
    DDTypeDetailResponse,
    QuestionCreate,
    QuestionResponse,
    QuestionUpdate,
    ReorderRequest,
    SectionCreate,
    SectionResponse,
    SectionUpdate,
)
from app.services import dd_types as dd_types_service
from app.services import questions as questions_service

router = APIRouter()


@router.get("/dd-types", response_model=list[DDTypeDetailResponse])
def list_dd_types_with_questions(
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """The DD types the user may see, with their sections and questions."""
    return dd_types_service.list_dd_types(
        db, current_user, active_only=active_only, with_questions=True
    )


@router.get("/dd-types/{dd_type_code}", response_model=DDTypeDetailResponse)
def get_dd_type_with_questions(
    dd_type_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """A DD type with its sections and questions."""
    return dd_types_service.get_with_questions(db, dd_type_code, current_user)


@router.get(
    "/dd-types/{dd_type_code}/sections/{section_id}/questions",
    response_model=list[QuestionResponse],
)
def list_section_questions(
    dd_type_code: str,
    section_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """The questions of a section, in order."""
    return questions_service.section_questions(db, dd_type_code, section_id, current_user)


@router.post(
    "/dd-types/{dd_type_code}/sections/{section_id}/questions", response_model=QuestionResponse
)
def create_question(
    dd_type_code: str,
    section_id: int,
    data: QuestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Add a question to a section; without a code, it takes the next one."""
    return questions_service.create_question(db, dd_type_code, section_id, data, current_user)


@router.put("/questions/{question_id}", response_model=QuestionResponse)
def update_question(
    question_id: int,
    data: QuestionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return questions_service.update_question(db, question_id, data, current_user)


@router.delete("/questions/{question_id}")
def delete_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    questions_service.delete_question(db, question_id, current_user)
    return {"message": "Question deleted successfully"}


@router.post("/dd-types/{dd_type_code}/sections", response_model=SectionResponse)
def create_section(
    dd_type_code: str,
    data: SectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Add a section, with the next letter."""
    return questions_service.create_section(db, dd_type_code, data, current_user)


@router.put("/sections/{section_id}", response_model=SectionResponse)
def update_section(
    section_id: int,
    data: SectionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return questions_service.update_section(db, section_id, data, current_user)


@router.delete("/sections/{section_id}")
def delete_section(
    section_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a section and its questions."""
    questions_service.delete_section(db, section_id, current_user)
    return {"message": "Section deleted successfully"}


@router.patch("/sections/{section_id}/reorder", response_model=SectionResponse)
def reorder_section(
    section_id: int,
    request: ReorderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Swap a section with the one at `new_order`."""
    return questions_service.move_section(db, section_id, request.new_order, current_user)


@router.patch("/questions/{question_id}/reorder", response_model=QuestionResponse)
def reorder_question(
    question_id: int,
    request: ReorderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Swap a question with the one at `new_order` in its section."""
    return questions_service.move_question(db, question_id, request.new_order, current_user)
