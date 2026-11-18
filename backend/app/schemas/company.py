from datetime import datetime

from pydantic import BaseModel


class CompanyCreate(BaseModel):
    name: str
    website_url: str | None = None
    description: str | None = None
    management_company_name: str | None = None
    management_company_website: str | None = None


class CompanyResponse(BaseModel):
    id: int
    name: str
    website_url: str | None
    description: str | None
    management_company_name: str | None = None
    management_company_website: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
