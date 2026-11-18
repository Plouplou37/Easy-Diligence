"""Companies under review: the fund, and the company that manages it."""

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.base import stored_id
from app.models.company import Company, CompanyCreate
from app.models.user import User
from app.services.authz import (
    assert_company_ownership,
    assert_company_view,
    filter_companies_for_user,
)


def list_companies(db: Session, user: User, skip: int = 0, limit: int = 100) -> list[Company]:
    """The companies the user may see: theirs and the shared ones (an admin's: all)."""
    return filter_companies_for_user(db.query(Company), user).offset(skip).limit(limit).all()


def get_company(db: Session, company_id: int, user: User) -> Company:
    """A company the user may see (404 otherwise, so ids cannot be probed)."""
    company = db.get(Company, company_id)
    if company is None:
        raise NotFoundError("Company not found")
    assert_company_view(company, user)
    return company


def create_company(db: Session, data: CompanyCreate, user: User) -> Company:
    company = Company(**data.model_dump(), created_by=stored_id(user))
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def update_company(db: Session, company_id: int, data: CompanyCreate, user: User) -> Company:
    """Replace a company's details (its creator or an admin)."""
    company = get_company(db, company_id, user)
    assert_company_ownership(company, user)
    for field, value in data.model_dump().items():
        setattr(company, field, value)
    company.updated_by = stored_id(user)
    db.commit()
    db.refresh(company)
    return company
