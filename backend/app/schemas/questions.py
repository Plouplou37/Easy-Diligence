from pydantic import BaseModel


class QuestionResponse(BaseModel):
    id: int
    question_code: str
    question_text: str
    context_prompt: str | None
    order_index: int

    class Config:
        from_attributes = True


class SectionResponse(BaseModel):
    id: int
    section_code: str
    title: str
    description: str | None
    order_index: int
    questions: list[QuestionResponse]

    class Config:
        from_attributes = True


class DDTypeDetailResponse(BaseModel):
    code: str
    name: str
    description: str | None
    icon: str | None
    is_active: bool
    is_validated: bool
    sections: list[SectionResponse] = []

    class Config:
        from_attributes = True


class QuestionCreate(BaseModel):
    question_code: str | None = None
    question_text: str
    context_prompt: str | None = None
    order_index: int = 0


class QuestionUpdate(BaseModel):
    question_code: str | None = None
    question_text: str | None = None
    context_prompt: str | None = None
    order_index: int | None = None


class SectionCreate(BaseModel):
    title: str
    description: str | None = None
    order_index: int | None = None


class SectionUpdate(BaseModel):
    section_code: str | None = None
    title: str | None = None
    description: str | None = None
    order_index: int | None = None


class ReorderRequest(BaseModel):
    new_order: int
