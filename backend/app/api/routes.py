from fastapi import APIRouter
from app.api import auth, admin, company, session, documents, processing, answers, websocket, questions, dd_types, executions, summaries, dashboard

api_router = APIRouter()

# Authentication routes (no authentication required)
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])

# Admin routes (admin authentication required)
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])

# Business routes (authentication required for these)
api_router.include_router(company.router, prefix="/company", tags=["company"])
api_router.include_router(session.router, prefix="/session", tags=["session"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(processing.router, prefix="/processing", tags=["processing"])
api_router.include_router(answers.router, prefix="/answers", tags=["answers"])
api_router.include_router(questions.router, prefix="/questions", tags=["questions"])
api_router.include_router(dd_types.router, prefix="/dd-types", tags=["dd-types"])

# New workflow-related routes
api_router.include_router(executions.router, prefix="/executions", tags=["executions"])
api_router.include_router(summaries.router, prefix="/summaries", tags=["summaries"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])

from app.api.vector_stores import router as vector_stores_router
api_router.include_router(vector_stores_router, prefix="/vector-stores", tags=["vector-stores"])

api_router.include_router(websocket.router, prefix="/ws", tags=["websocket"])