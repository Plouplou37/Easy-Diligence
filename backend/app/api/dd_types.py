from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.dd_types import DDType as DDTypeModel, DEFAULT_DD_TYPE_ICON
from app.models.questions import DDSection, DDQuestion
from app.models.user import User
from app.dependencies import get_current_active_user, get_current_admin_user
from app.core.authz import (
    filter_dd_types_for_user,
    assert_dd_type_view,
    assert_dd_type_ownership,
)
from app.schemas.dd_types import DDTypeCreate, DDTypeUpdate, DDTypeResponse
from app.core.cache import cache_response, CacheInvalidator
from app.core.file_parser import DDTypeFileParser, FileParsingError
from typing import Optional, List
from datetime import datetime

router = APIRouter()

# Helper function to get DD type by code
def get_dd_type_by_code(db: Session, code: str) -> DDTypeModel:
    """Helper function to get DD type by code and raise 404 if not found"""
    dd_type = db.query(DDTypeModel).filter(DDTypeModel.code == code).first()
    if not dd_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DD type with code '{code}' not found"
        )
    return dd_type


@router.get("/", response_model=List[DDTypeResponse])
async def list_dd_types(
    active_only: bool = True,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List DD types visible to the current user (own + shared system types)"""
    query = db.query(DDTypeModel)

    if active_only:
        query = query.filter(DDTypeModel.is_active == True)

    # Per-user visibility: admins see all, others see shared + their own
    query = filter_dd_types_for_user(query, current_user)

    dd_types = query.order_by(DDTypeModel.order_index, DDTypeModel.name).offset(skip).limit(limit).all()
    return dd_types

@router.post("/import", response_model=DDTypeResponse)
async def create_dd_type_from_file(
    code: str = Form(...),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    icon: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new DD type from uploaded file (Excel, CSV, or JSON)"""

    # Check if code already exists
    existing = db.query(DDTypeModel).filter(DDTypeModel.code == code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="DD type code already exists"
        )

    try:
        # Parse the uploaded file
        parser = DDTypeFileParser()
        file_content = await file.read()
        sections_data = parser.parse_file(file_content, file.filename)

        if not sections_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid data found in the uploaded file"
            )

        # Create the DD type
        db_dd_type = DDTypeModel(
            code=code,
            name=name,
            description=description,
            icon=icon or DEFAULT_DD_TYPE_ICON,
            order_index=0,
            is_active=True,
            is_system=False,
            created_by=current_user.id
        )

        db.add(db_dd_type)
        db.flush()

        # Create sections and questions
        for section_order, section_data in enumerate(sections_data):
            # Create section
            db_section = DDSection(
                dd_type_id=db_dd_type.id,
                section_code=section_data["section_code"],
                title=section_data["title"],
                # No placeholder. This used to default to "Section for <title>",
                # which filled 213 of 217 rows with a restatement of the title.
                # The description is now sent to the model alongside the section
                # heading, so an empty one is better than a tautological one.
                description=section_data.get("description"),
                order_index=section_data["order_index"]
            )

            db.add(db_section)
            db.flush()

            # Create questions for this section
            for question_data in section_data["questions"]:
                db_question = DDQuestion(
                    section_id=db_section.id,
                    question_code=question_data["question_code"],
                    question_text=question_data["question_text"],
                    context_prompt=question_data.get("context_prompt"),
                    order_index=question_data["order_index"]
                )

                db.add(db_question)

        db.commit()
        db.refresh(db_dd_type)

        return db_dd_type

    except FileParsingError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File parsing error: {str(e)}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating DD type from file: {str(e)}"
        )

@router.get("/{dd_type_code}", response_model=DDTypeResponse)
async def get_dd_type(
    dd_type_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific DD type by code"""
    dd_type = db.query(DDTypeModel).filter(DDTypeModel.code == dd_type_code).first()
    if not dd_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DD type not found"
        )
    assert_dd_type_view(dd_type, current_user)
    return dd_type

@router.get("/code/{code}", response_model=DDTypeResponse)
async def get_dd_type_by_code(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a DD type by its code"""
    dd_type = db.query(DDTypeModel).filter(DDTypeModel.code == code).first()
    if not dd_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DD type not found"
        )
    assert_dd_type_view(dd_type, current_user)
    return dd_type

@router.post("/", response_model=DDTypeResponse)
async def create_dd_type(
    dd_type: DDTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new DD type"""
    # Check if code already exists
    existing = db.query(DDTypeModel).filter(DDTypeModel.code == dd_type.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="DD type code already exists"
        )

    db_dd_type = DDTypeModel(
        code=dd_type.code,
        name=dd_type.name,
        description=dd_type.description,
        icon=dd_type.icon,
        order_index=dd_type.order_index,
        is_active=True,
        is_system=False,
        created_by=current_user.id
    )
    
    db.add(db_dd_type)
    db.commit()
    db.refresh(db_dd_type)

    return db_dd_type

@router.put("/{dd_type_code}", response_model=DDTypeResponse)
async def update_dd_type(
    dd_type_code: str,
    dd_type_update: DDTypeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update an existing DD type"""
    dd_type = db.query(DDTypeModel).filter(DDTypeModel.code == dd_type_code).first()
    if not dd_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DD type not found"
        )

    # Only the owner (or an admin) may modify this DD type
    assert_dd_type_ownership(dd_type, current_user)

    # Check if trying to update a system DD type's critical fields
    if dd_type.is_system and dd_type_update.code and dd_type_update.code != dd_type.code:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot change code of system DD type"
        )
    
    # Check if new code conflicts with existing one
    if dd_type_update.code and dd_type_update.code != dd_type.code:
        existing = db.query(DDTypeModel).filter(DDTypeModel.code == dd_type_update.code).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="DD type code already exists"
            )
    
    # Update fields
    update_data = dd_type_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(dd_type, field, value)
    
    db.commit()
    db.refresh(dd_type)
    
    return dd_type

@router.delete("/{dd_type_code}")
async def delete_dd_type(
    dd_type_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a DD type (only if not system type and not in use)"""
    dd_type = db.query(DDTypeModel).filter(DDTypeModel.code == dd_type_code).first()
    if not dd_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DD type not found"
        )

    # Only the owner (or an admin) may delete this DD type
    assert_dd_type_ownership(dd_type, current_user)

    # Check if it's a system DD type
    if dd_type.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete system DD type"
        )
    
    # Check if it's in use (has execution records)
    # Sections are just structure and can be cascade-deleted
    if dd_type.executions:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete DD type that is in use. Set to inactive instead."
        )
    
    db.delete(dd_type)
    db.commit()

    return {"message": "DD type deleted successfully"}

@router.post("/{dd_type_code}/activate")
async def activate_dd_type(
    dd_type_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Activate a DD type"""
    dd_type = db.query(DDTypeModel).filter(DDTypeModel.code == dd_type_code).first()
    if not dd_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DD type not found"
        )

    assert_dd_type_ownership(dd_type, current_user)

    dd_type.is_active = True
    db.commit()
    db.refresh(dd_type)

    return {"message": "DD type activated successfully"}

@router.post("/{dd_type_code}/deactivate")
async def deactivate_dd_type(
    dd_type_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Deactivate a DD type"""
    dd_type = db.query(DDTypeModel).filter(DDTypeModel.code == dd_type_code).first()
    if not dd_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DD type not found"
        )

    assert_dd_type_ownership(dd_type, current_user)

    dd_type.is_active = False
    db.commit()
    db.refresh(dd_type)

    return {"message": "DD type deactivated successfully"}

@router.put("/{dd_type_code}/validate", response_model=DDTypeResponse)
async def validate_dd_type(
    dd_type_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Validate and lock a DD type, making it immutable - owner or admin"""
    # Get the DD type
    dd_type = db.query(DDTypeModel).filter(DDTypeModel.code == dd_type_code).first()
    if not dd_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DD type not found"
        )

    # Only the owner (or an admin) may validate/lock this DD type
    assert_dd_type_ownership(dd_type, current_user)

    # Check if already validated
    if dd_type.is_validated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"DD type '{dd_type.name}' is already validated and locked"
        )
    
    # Validate the DD type by setting is_validated to True
    dd_type.is_validated = True

    db.commit()
    db.refresh(dd_type)

    return dd_type

