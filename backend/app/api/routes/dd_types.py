"""DD types (questionnaires): listing, creation (blank or from a file), changes,
activation, validation, deletion."""

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.api.uploads import QUESTIONNAIRE_EXTENSIONS, read_upload
from app.core.database import get_db
from app.models.dd_types import DDTypeCreate, DDTypeResponse, DDTypeUpdate
from app.models.user import User
from app.services import dd_types as dd_types_service

router = APIRouter()


@router.get("/", response_model=list[DDTypeResponse])
def list_dd_types(
    active_only: bool = True,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """The DD types the user may see: theirs and the shared ones."""
    return dd_types_service.list_dd_types(
        db, current_user, active_only=active_only, skip=skip, limit=limit
    )


@router.post("/import", response_model=DDTypeResponse)
async def create_dd_type_from_file(
    code: str = Form(...),
    name: str = Form(...),
    description: str | None = Form(None),
    icon: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a DD type from a questionnaire file (Excel, CSV or JSON)."""
    content = await read_upload(file, allowed_extensions=QUESTIONNAIRE_EXTENSIONS)
    return await run_in_threadpool(
        dd_types_service.import_dd_type,
        db,
        current_user,
        code=code,
        name=name,
        description=description,
        icon=icon,
        content=content,
        filename=file.filename or "",
    )


@router.get("/{dd_type_code}", response_model=DDTypeResponse)
def get_dd_type(
    dd_type_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """A DD type the user may see."""
    return dd_types_service.get_dd_type_by_code(db, dd_type_code, current_user)


@router.post("/", response_model=DDTypeResponse)
def create_dd_type(
    data: DDTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create an empty DD type, owned by the user."""
    return dd_types_service.create_dd_type(db, data, current_user)


@router.put("/{dd_type_code}", response_model=DDTypeResponse)
def update_dd_type(
    dd_type_code: str,
    data: DDTypeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Change a DD type (its owner or an admin)."""
    dd_type = dd_types_service.get_owned_dd_type(db, dd_type_code, current_user)
    return dd_types_service.update_dd_type(db, dd_type, data)


@router.delete("/{dd_type_code}")
def delete_dd_type(
    dd_type_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a DD type that has never been run."""
    dd_type = dd_types_service.get_owned_dd_type(db, dd_type_code, current_user)
    dd_types_service.delete_dd_type(db, dd_type)
    return {"message": "DD type deleted successfully"}


@router.post("/{dd_type_code}/activate")
def activate_dd_type(
    dd_type_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Offer the DD type for new sessions."""
    dd_type = dd_types_service.get_owned_dd_type(db, dd_type_code, current_user)
    dd_types_service.set_active(db, dd_type, True)
    return {"message": "DD type activated successfully"}


@router.post("/{dd_type_code}/deactivate")
def deactivate_dd_type(
    dd_type_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Stop offering the DD type for new sessions."""
    dd_type = dd_types_service.get_owned_dd_type(db, dd_type_code, current_user)
    dd_types_service.set_active(db, dd_type, False)
    return {"message": "DD type deactivated successfully"}


@router.put("/{dd_type_code}/validate", response_model=DDTypeResponse)
def validate_dd_type(
    dd_type_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Freeze a DD type's structure. Irreversible."""
    dd_type = dd_types_service.get_owned_dd_type(db, dd_type_code, current_user)
    return dd_types_service.validate_dd_type(db, dd_type)
