import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.api.router import api_router
from app.core.config import settings
from app.core.database import Base, engine
from app.core.exceptions import (
    AppError,
    ConflictError,
    ExternalServiceError,
    InvalidRequestError,
    NotFoundError,
    PermissionDeniedError,
    TooManyRequestsError,
)

logger = logging.getLogger(__name__)

# HTTP status of each business error (core/exceptions.py).
ERROR_STATUS = {
    InvalidRequestError: 400,
    PermissionDeniedError: 403,
    NotFoundError: 404,
    ConflictError: 409,
    TooManyRequestsError: 429,
    ExternalServiceError: 502,
}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


class UnhandledErrorMiddleware:
    """Last safety net: an unexpected exception is logged with its traceback
    and answered with a generic 500, never with its message.

    Installed inside CORSMiddleware, so that answer still carries the CORS
    headers. Without it, a 500 reached the browser without them and showed up
    as a misleading "CORS error". Plain ASGI rather than BaseHTTPMiddleware,
    which interferes with background tasks.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_started = False

        async def send_tracking(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, send_tracking)
        except Exception:
            logger.exception("Unhandled error on %s %s", scope.get("method"), scope.get("path"))
            if response_started:
                raise
            response = JSONResponse({"detail": "Internal server error"}, status_code=500)
            await response(scope, receive, send)


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
)

# Order matters: the middleware added last runs first. CORS must wrap the
# safety net so that its 500s get CORS headers too.
app.add_middleware(UnhandledErrorMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    status_code = next((code for cls, code in ERROR_STATUS.items() if isinstance(exc, cls)), 400)
    headers = None
    if isinstance(exc, TooManyRequestsError):
        headers = {"Retry-After": str(exc.retry_after)}
    if status_code >= 500:
        logger.error("%s: %s", type(exc).__name__, exc.message, exc_info=exc)
    return JSONResponse({"detail": exc.message}, status_code=status_code, headers=headers)


app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    return {"message": f"{settings.app_name} API"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
