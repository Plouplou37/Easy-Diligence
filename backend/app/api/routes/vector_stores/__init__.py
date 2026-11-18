"""Vector stores API: the stores, their files, and their assignment to sessions."""

from fastapi import APIRouter

from .core import router as core_router
from .files import router as files_router
from .sessions import router as sessions_router

router = APIRouter()

# Sessions first: "/session/..." must not be read as a vector store id.
router.include_router(sessions_router, tags=["vector-stores-sessions"])
router.include_router(core_router, tags=["vector-stores-core"])
router.include_router(files_router, tags=["vector-stores-files"])
