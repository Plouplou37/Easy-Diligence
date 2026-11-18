from fastapi import APIRouter

from app.api.routes import (
    admin,
    answers,
    auth,
    company,
    dashboard,
    dd_types,
    processing,
    questions,
    session,
    summaries,
)
from app.api.routes.vector_stores import router as vector_stores_router

api_router = APIRouter()

# Authentication routes (no authentication required)
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])

# Admin routes (admin authentication required)
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])

# Business routes (authentication required for these)
api_router.include_router(company.router, prefix="/company", tags=["company"])
api_router.include_router(session.router, prefix="/session", tags=["session"])
api_router.include_router(processing.router, prefix="/processing", tags=["processing"])
api_router.include_router(answers.router, prefix="/answers", tags=["answers"])
api_router.include_router(questions.router, prefix="/questions", tags=["questions"])
api_router.include_router(dd_types.router, prefix="/dd-types", tags=["dd-types"])
api_router.include_router(summaries.router, prefix="/summaries", tags=["summaries"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(vector_stores_router, prefix="/vector-stores", tags=["vector-stores"])
