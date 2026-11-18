
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.cache import CacheInvalidator
from app.core.database import get_db
from app.models.company import Company
from app.models.user import User
from app.schemas.company import CompanyCreate, CompanyResponse
from app.services.authz import (
    assert_company_ownership,
    assert_company_view,
    filter_companies_for_user,
)

router = APIRouter()

@router.post("/", response_model=CompanyResponse)
async def create_company(
    company: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new company"""
    db_company = Company(
        name=company.name,
        website_url=company.website_url,
        description=company.description,
        management_company_name=company.management_company_name,
        management_company_website=company.management_company_website,
        created_by=current_user.id
    )
    db.add(db_company)
    db.commit()
    db.refresh(db_company)

    # Invalidate company caches after creating new company
    CacheInvalidator.invalidate_company_cache()

    return db_company

@router.get("/", response_model=list[CompanyResponse])
async def list_companies(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List companies visible to the current user (own + shared; admins see all)"""
    query = filter_companies_for_user(db.query(Company), current_user)
    companies = query.offset(skip).limit(limit).all()
    return companies

@router.get("/auth-test")
async def test_auth_endpoint_moved(
    current_user: User = Depends(get_current_active_user)
):
    """Test endpoint to verify authentication is working - moved before parametrized route"""
    return {"message": "Authentication working", "user": current_user.email}

@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific company"""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    # Per-user isolation: non-admins can only view their own / shared companies
    assert_company_view(company, current_user)
    return company

@router.put("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: int,
    company_update: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a company"""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )

    # Per-user isolation: only the owner (or an admin) may modify
    assert_company_ownership(company, current_user)

    company.name = company_update.name
    company.website_url = company_update.website_url
    company.description = company_update.description
    company.management_company_name = company_update.management_company_name
    company.management_company_website = company_update.management_company_website
    company.updated_by = current_user.id

    db.commit()
    db.refresh(company)

    # Invalidate company caches after updating
    CacheInvalidator.invalidate_company_cache()

    return company
