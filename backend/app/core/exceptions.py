"""Business errors, raised by services and the engine.

No FastAPI here: app/main.py maps each class to an HTTP status. The message of
these errors is written for the user and is sent to the client as is. Any
other exception is logged with its traceback and answered with a generic 500,
so an internal message (a driver error, an OpenAI response) never leaves the
server.
"""


class AppError(Exception):
    """Base class: an expected failure whose message is safe to show."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class InvalidRequestError(AppError):
    """The request cannot be honoured as sent (HTTP 400)."""


class PermissionDeniedError(AppError):
    """The user may not do this (HTTP 403)."""


class NotFoundError(AppError):
    """The thing asked for does not exist, or is not visible to the user (HTTP 404)."""


class ConflictError(AppError):
    """The request clashes with the current state (HTTP 409)."""


class TooManyRequestsError(AppError):
    """Too many attempts; retry after `retry_after` seconds (HTTP 429)."""

    def __init__(self, message: str, retry_after: int):
        super().__init__(message)
        self.retry_after = retry_after


class ExternalServiceError(AppError):
    """A provider (OpenAI, SMTP...) failed. The message stays generic (HTTP 502)."""
