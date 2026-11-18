from pydantic import BaseModel
from typing import Optional, List


class QuestionResponse(BaseModel):
    id: int
    question_code: str
    question_text: str
    context_prompt: Optional[str]
    order_index: int

    class Config:
        from_attributes = True


class SectionResponse(BaseModel):
    id: int
    section_code: str
    title: str
    description: Optional[str]
    order_index: int
    questions: List[QuestionResponse]
    
    class Config:
        from_attributes = True


class DDTypeDetailResponse(BaseModel):
    code: str
    name: str
    description: Optional[str]
    icon: Optional[str]
    is_active: bool
    is_validated: bool
    sections: List[SectionResponse] = []
    
    class Config:
        from_attributes = True


class QuestionCreate(BaseModel):
    question_code: Optional[str] = None
    question_text: str
    context_prompt: Optional[str] = None
    order_index: int = 0


class QuestionUpdate(BaseModel):
    question_code: Optional[str] = None
    question_text: Optional[str] = None
    context_prompt: Optional[str] = None
    order_index: Optional[int] = None


class SectionCreate(BaseModel):
    title: str
    description: Optional[str] = None
    order_index: Optional[int] = None


class SectionUpdate(BaseModel):
    section_code: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    order_index: Optional[int] = None


class ReorderRequest(BaseModel):
    new_order: int