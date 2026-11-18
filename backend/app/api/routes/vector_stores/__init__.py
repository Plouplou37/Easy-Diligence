"""
Vector Store API - Modularized
Combines all vector store functionality in focused modules
"""
from fastapi import APIRouter
from .core import router as core_router
from .files import router as files_router
from .sessions import router as sessions_router
from .search import router as search_router

# Main router combining all sub-modules
router = APIRouter()

# Include all sub-routers
router.include_router(sessions_router, tags=["vector-stores-sessions"])
router.include_router(core_router, tags=["vector-stores-core"])  
router.include_router(files_router, tags=["vector-stores-files"])
router.include_router(search_router, tags=["vector-stores-search"])