from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CompanyCreate(BaseModel):
    name: str
    website_url: Optional[str] = None
    description: Optional[str] = None
    management_company_name: Optional[str] = None
    management_company_website: Optional[str] = None


class CompanyResponse(BaseModel):
    id: int
    name: str
    website_url: Optional[str]
    description: Optional[str]
    management_company_name: Optional[str] = None
    management_company_website: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True