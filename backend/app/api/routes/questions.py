import random
import time

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.dd_types import DDType as DDTypeModel
from app.models.questions import DDQuestion, DDSection
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
from app.services.authz import (
    assert_dd_type_ownership,
    assert_dd_type_view,
    filter_dd_types_for_user,
)

router = APIRouter()


# Helper function to get DD type by code
def get_dd_type_by_code(db: Session, code: str) -> DDTypeModel:
    """Helper function to get DD type by code and raise 404 if not found"""
    dd_type = db.query(DDTypeModel).filter(DDTypeModel.code == code).first()
    if not dd_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"DD type with code '{code}' not found"
        )
    return dd_type


# Helper Functions (Simplified Validation Lock System)
def check_dd_type_immutability(dd_type_code: str, db: Session, current_user: User = None) -> None:
    """
    Check if DD type can be modified according to the simplified validation lock system.

    DD types become read-only once they are manually validated (is_validated = True).
    If validated, raises HTTPException directing user to create new DD type.
    If not validated, allows direct modification (DD type is still "draft").

    When ``current_user`` is provided, also enforces per-user ownership: only the
    owner (or an admin) may modify the DD type.
    """

    # Get DD type and check validation status
    dd_type = db.query(DDTypeModel).filter(DDTypeModel.code == dd_type_code).first()
    if not dd_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DD type not found")

    # Per-user ownership check (owner or admin only)
    if current_user is not None:
        assert_dd_type_ownership(dd_type, current_user)

    if dd_type.is_validated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"DD type '{dd_type.name}' has been validated and is now immutable. "
            f"Cannot modify validated DD types to maintain data integrity. "
            f"Please create a new DD type if you need to make changes.",
        )


def check_section_dd_type_immutability(
    section_id: int, db: Session, current_user: User = None
) -> None:
    """Check if the DD type containing this section can be modified."""
    section = (
        db.query(DDSection)
        .options(joinedload(DDSection.dd_type_obj))
        .filter(DDSection.id == section_id)
        .first()
    )
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    check_dd_type_immutability(section.dd_type_obj.code, db, current_user)


def check_question_dd_type_immutability(
    question_id: int, db: Session, current_user: User = None
) -> None:
    """Check if the DD type containing this question can be modified."""
    question = db.query(DDQuestion).filter(DDQuestion.id == question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    check_section_dd_type_immutability(question.section_id, db, current_user)


@router.get("/dd-types", response_model=list[DDTypeDetailResponse])
async def list_dd_types_with_questions(
    dd_type: str | None = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List DD types (with question structure) visible to the current user"""
    query = db.query(DDTypeModel).options(
        joinedload(DDTypeModel.sections).joinedload(DDSection.questions)
    )

    if active_only:
        query = query.filter(DDTypeModel.is_active == True)

    # Per-user visibility: admins see all, others see shared + their own
    query = filter_dd_types_for_user(query, current_user)

    dd_types = query.all()
    return dd_types


@router.get("/dd-types/{dd_type_code}", response_model=DDTypeDetailResponse)
async def get_dd_type_with_questions(
    dd_type_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a specific DD type with all sections and questions"""
    dd_type = (
        db.query(DDTypeModel)
        .options(joinedload(DDTypeModel.sections).joinedload(DDSection.questions))
        .filter(DDTypeModel.code == dd_type_code)
        .first()
    )

    if not dd_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DD type not found")
    assert_dd_type_view(dd_type, current_user)
    return dd_type


@router.get(
    "/dd-types/{dd_type_code}/sections/{section_id}/questions",
    response_model=list[QuestionResponse],
)
async def list_section_questions(
    dd_type_code: str,
    section_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all questions in a specific section"""
    # Get DD type by code to get its ID
    dd_type = get_dd_type_by_code(db, dd_type_code)
    assert_dd_type_view(dd_type, current_user)

    # Verify section belongs to DD type
    section = (
        db.query(DDSection)
        .filter(DDSection.id == section_id, DDSection.dd_type_id == dd_type.id)
        .first()
    )

    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")

    questions = (
        db.query(DDQuestion)
        .filter(DDQuestion.section_id == section_id)
        .order_by(DDQuestion.order_index)
        .all()
    )

    return questions


@router.post(
    "/dd-types/{dd_type_code}/sections/{section_id}/questions", response_model=QuestionResponse
)
async def create_question(
    dd_type_code: str,
    section_id: int,
    question: QuestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new question in a section - protected by validation lock"""
    # Check ownership + DD type validation status before allowing modifications
    check_dd_type_immutability(dd_type_code, db, current_user)

    # Get DD type by code to get its ID
    dd_type = get_dd_type_by_code(db, dd_type_code)

    # Verify section belongs to DD type
    section = (
        db.query(DDSection)
        .filter(DDSection.id == section_id, DDSection.dd_type_id == dd_type.id)
        .first()
    )

    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")

    # Auto-generate question_code if not provided
    if not question.question_code:
        # Create question prefix from question_text (first 6 chars, cleaned)
        text_prefix = (
            question.question_text.upper().replace(" ", "").replace("_", "")[:6] or "QUESTION"
        )
        text_prefix = "".join(c for c in text_prefix if c.isalnum())[:6]
        if len(text_prefix) < 3:
            text_prefix = "QUESTION"

        # Generate unique suffix using timestamp and random number
        timestamp = str(int(time.time()))[-6:]  # Last 6 digits of timestamp
        random_suffix = str(random.randint(10, 99))  # 2-digit random number

        question_code = f"{text_prefix}_{timestamp}{random_suffix}"
    else:
        question_code = question.question_code

    # Check for duplicate question_code within the section
    existing = (
        db.query(DDQuestion)
        .filter(DDQuestion.section_id == section_id, DDQuestion.question_code == question_code)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question code already exists in this section",
        )

    db_question = DDQuestion(
        section_id=section_id,
        question_code=question_code,
        question_text=question.question_text,
        context_prompt=question.context_prompt,
        order_index=question.order_index,
    )

    db.add(db_question)
    db.commit()
    db.refresh(db_question)

    return db_question


@router.put("/questions/{question_id}", response_model=QuestionResponse)
async def update_question(
    question_id: int,
    question_update: QuestionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update an existing question - protected by validation lock"""
    # Check ownership + DD type validation status before allowing modifications
    check_question_dd_type_immutability(question_id, db, current_user)

    question = db.query(DDQuestion).filter(DDQuestion.id == question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    # Update fields if provided
    update_data = question_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(question, field, value)

    db.commit()
    db.refresh(question)

    return question


@router.delete("/questions/{question_id}")
async def delete_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a question - protected by validation lock"""
    # Check ownership + DD type validation status before allowing modifications
    check_question_dd_type_immutability(question_id, db, current_user)

    question = db.query(DDQuestion).filter(DDQuestion.id == question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    db.delete(question)
    db.commit()

    return {"message": "Question deleted successfully"}


@router.post("/dd-types/{dd_type_code}/sections", response_model=SectionResponse)
async def create_section(
    dd_type_code: str,
    section: SectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new section in a DD type - protected by validation lock"""

    # Verify DD type exists
    dd_type = db.query(DDTypeModel).filter(DDTypeModel.code == dd_type_code).first()
    if not dd_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DD type not found")

    # Check ownership + DD type validation status before allowing modifications
    check_dd_type_immutability(dd_type_code, db, current_user)

    # Create section prefix from title (first 6 chars, cleaned)
    title_prefix = section.title.upper().replace(" ", "").replace("_", "")[:6] or "SECTION"
    title_prefix = "".join(c for c in title_prefix if c.isalnum())[:6]
    if len(title_prefix) < 3:
        title_prefix = "SECTION"

    # Generate unique suffix using timestamp and random number
    timestamp = str(int(time.time()))[-6:]  # Last 6 digits of timestamp
    random_suffix = str(random.randint(10, 99))  # 2-digit random number

    section_code = f"{title_prefix}_{timestamp}{random_suffix}"

    # Auto-calculate order_index if not provided
    if section.order_index is None:
        max_order = (
            db.query(func.max(DDSection.order_index))
            .filter(DDSection.dd_type_id == dd_type.id)
            .scalar()
            or -1
        )
        order_index = max_order + 1
    else:
        order_index = section.order_index

    db_section = DDSection(
        dd_type_id=dd_type.id,
        section_code=section_code,
        title=section.title,
        description=section.description,
        order_index=order_index,
    )

    db.add(db_section)
    db.commit()
    db.refresh(db_section)

    return db_section


@router.put("/sections/{section_id}", response_model=SectionResponse)
async def update_section(
    section_id: int,
    section_update: SectionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update an existing section - protected by validation lock"""
    # Check DD type validation status before allowing modifications
    check_section_dd_type_immutability(section_id, db, current_user)

    section = db.query(DDSection).filter(DDSection.id == section_id).first()
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")

    # Update fields if provided
    update_data = section_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(section, field, value)

    db.commit()
    db.refresh(section)

    return section


@router.delete("/sections/{section_id}")
async def delete_section(
    section_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a section and all its questions - protected by validation lock"""
    # Check DD type validation status before allowing modifications
    check_section_dd_type_immutability(section_id, db, current_user)

    section = db.query(DDSection).filter(DDSection.id == section_id).first()
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")

    db.delete(section)
    db.commit()

    return {"message": "Section deleted successfully"}


@router.patch("/sections/{section_id}/reorder", response_model=SectionResponse)
async def reorder_section(
    section_id: int,
    request: ReorderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Reorder a section - protected by validation lock"""
    # Check DD type validation status before allowing modifications
    check_section_dd_type_immutability(section_id, db, current_user)

    section = db.query(DDSection).filter(DDSection.id == section_id).first()
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")

    # Find the target section with the desired order_index
    target_section = (
        db.query(DDSection)
        .filter(
            DDSection.dd_type_id == section.dd_type_id, DDSection.order_index == request.new_order
        )
        .first()
    )

    if target_section:
        # Swap order_index values
        temp_order = section.order_index
        section.order_index = target_section.order_index
        target_section.order_index = temp_order

    db.commit()
    db.refresh(section)

    return section


@router.patch("/questions/{question_id}/reorder", response_model=QuestionResponse)
async def reorder_question(
    question_id: int,
    request: ReorderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Reorder a question - protected by validation lock"""
    # Check ownership + DD type validation status before allowing modifications
    check_question_dd_type_immutability(question_id, db, current_user)

    question = db.query(DDQuestion).filter(DDQuestion.id == question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    # Find the target question with the desired order_index
    target_question = (
        db.query(DDQuestion)
        .filter(
            DDQuestion.section_id == question.section_id,
            DDQuestion.order_index == request.new_order,
        )
        .first()
    )

    if target_question:
        # Swap order_index values
        temp_order = question.order_index
        question.order_index = target_question.order_index
        target_question.order_index = temp_order

    db.commit()
    db.refresh(question)

    return question
