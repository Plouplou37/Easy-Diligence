"""Companies under review."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.company import CompanyCreate, CompanyResponse
from app.models.user import User
from app.services import companies

router = APIRouter()


@router.post("/", response_model=CompanyResponse)
def create_company(
    data: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return companies.create_company(db, data, current_user)


@router.get("/", response_model=list[CompanyResponse])
def list_companies(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """The companies the user may see: theirs and the shared ones."""
    return companies.list_companies(db, current_user, skip, limit)


@router.get("/{company_id}", response_model=CompanyResponse)
def get_company(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return companies.get_company(db, company_id, current_user)


@router.put("/{company_id}", response_model=CompanyResponse)
def update_company(
    company_id: int,
    data: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Replace a company's details (its creator or an admin)."""
    return companies.update_company(db, company_id, data, current_user)
