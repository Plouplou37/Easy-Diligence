"""What went wrong with a question, decided by the class of the error, never by
its text: whether to try again, how long to wait, and what to tell the user.

The text of an OpenAI error stays in the logs. The user reads a message
written for them, chosen by the type of the error (MESSAGES).
"""

from dataclasses import dataclass

import openai

from app.models.answer import ErrorType


class ResponseError(RuntimeError):
    """OpenAI answered, but with nothing usable: no response, or a response
    that did not complete (engine/openai_client.py)."""


@dataclass(frozen=True)
class Failure:
    """An error, classified."""

    type: ErrorType
    retryable: bool


def classify(error: BaseException) -> Failure:
    """The type of an error, and whether trying again may help."""
    # APITimeoutError is an APIConnectionError: it is tested first.
    if isinstance(error, openai.RateLimitError):
        return Failure(ErrorType.RATE_LIMIT, True)
    if isinstance(error, openai.APITimeoutError):
        return Failure(ErrorType.TIMEOUT, True)
    if isinstance(error, openai.APIConnectionError):
        return Failure(ErrorType.NETWORK_ERROR, True)
    if isinstance(error, openai.BadRequestError):
        if error.code == "context_length_exceeded":
            return Failure(ErrorType.CONTEXT_OVERFLOW, False)
        return Failure(ErrorType.VALIDATION_ERROR, False)
    if isinstance(error, openai.UnprocessableEntityError):
        return Failure(ErrorType.VALIDATION_ERROR, False)
    if isinstance(error, openai.AuthenticationError | openai.PermissionDeniedError):
        # Global and final: no question will go through (is_global).
        return Failure(ErrorType.API_ERROR, False)
    if isinstance(error, openai.APIStatusError) and error.status_code >= 500:
        return Failure(ErrorType.API_ERROR, True)
    if isinstance(error, ResponseError):
        return Failure(ErrorType.API_ERROR, True)
    return Failure(ErrorType.UNKNOWN, True)


# Errors that every question would meet (quota, network, OpenAI down, key
# refused), as opposed to those of one question: the circuit breaker counts them.
GLOBAL_ERRORS = (ErrorType.RATE_LIMIT, ErrorType.NETWORK_ERROR, ErrorType.API_ERROR)


def is_global(error_type: ErrorType) -> bool:
    return error_type in GLOBAL_ERRORS


# Seconds before the first retry, doubled at each attempt.
_BASE_DELAY = {
    ErrorType.RATE_LIMIT: 5.0,
    ErrorType.NETWORK_ERROR: 2.0,
    ErrorType.CONTEXT_OVERFLOW: 0.5,
}
MAX_DELAY = 60.0


def retry_delay(error: BaseException, failure: Failure, attempt: int) -> float:
    """Seconds to wait before the next attempt (attempt 0 is the first retry).

    OpenAI's own Retry-After wins when it sends one (on a rate limit, mostly);
    otherwise an exponential backoff that depends on the type of error.
    """
    response = getattr(error, "response", None)
    headers = getattr(response, "headers", None)
    if headers is not None:
        for name, scale in (("retry-after-ms", 0.001), ("retry-after", 1.0)):
            try:
                seconds = float(headers.get(name)) * scale
            except (TypeError, ValueError):
                continue
            if seconds >= 0:
                return min(seconds, MAX_DELAY)
    base = _BASE_DELAY.get(failure.type, 1.0)
    return min(base * 2**attempt, MAX_DELAY)


# What the user reads on a failed question, in the language of the interface.
MESSAGES = {
    ErrorType.RATE_LIMIT: "OpenAI rate limit reached. Use Resume in a few minutes.",
    ErrorType.TIMEOUT: "OpenAI took too long to answer. Use Resume to try again.",
    ErrorType.NETWORK_ERROR: "OpenAI could not be reached. Use Resume once the connection is back.",
    ErrorType.CONTEXT_OVERFLOW: (
        "This question does not fit in the model's context window. "
        "Shorten it, or its documents, then regenerate it."
    ),
    ErrorType.VALIDATION_ERROR: (
        "OpenAI refused the request for this question. Check its text, then regenerate it."
    ),
    ErrorType.API_ERROR: (
        "OpenAI returned an error. Use Resume to try again; if it persists, "
        "check the OpenAI key and account."
    ),
    ErrorType.UNKNOWN: "The answer could not be generated. Use Resume to try again.",
}


def user_message(failure: Failure) -> str:
    return MESSAGES[failure.type]


KEY_REFUSED_IN_A_RUN = (
    "OpenAI refused the server's API key. Ask an administrator to check the "
    "OpenAI key and account, then use Resume."
)


def question_message(error: BaseException, failure: Failure) -> str:
    """The message of a question that failed in a run. A refused key is named:
    the API_ERROR type also covers OpenAI being down, which waiting fixes."""
    if isinstance(error, openai.AuthenticationError | openai.PermissionDeniedError):
        return KEY_REFUSED_IN_A_RUN
    return user_message(failure)


# What the user reads when an OpenAI call made for a request fails, outside a
# run (a vector store, a file): there is no Resume to point to.
OPERATION_MESSAGES = {
    ErrorType.RATE_LIMIT: "OpenAI rate limit reached. Try again in a few minutes.",
    ErrorType.TIMEOUT: "OpenAI took too long to answer. Try again in a moment.",
    ErrorType.NETWORK_ERROR: "OpenAI could not be reached. Try again in a moment.",
    ErrorType.CONTEXT_OVERFLOW: "OpenAI refused the request: it is too large.",
    ErrorType.VALIDATION_ERROR: (
        "OpenAI refused the request. Check what was sent (a file's type or size, "
        "a name), then try again."
    ),
    ErrorType.API_ERROR: (
        "OpenAI returned an error. Try again in a moment; if it persists, "
        "check the OpenAI key and account."
    ),
    ErrorType.UNKNOWN: "The operation failed at OpenAI. Try again in a moment.",
}

KEY_REFUSED = (
    "OpenAI refused the server's API key. Ask an administrator to check the OpenAI key and account."
)


def operation_message(error: BaseException) -> str:
    """The message for an OpenAI error that reached a route (app/main.py).

    A refused key gets its own message: it is the one case the user cannot
    wait out, and the API_ERROR type also covers OpenAI being down.
    """
    if isinstance(error, openai.AuthenticationError | openai.PermissionDeniedError):
        return KEY_REFUSED
    return OPERATION_MESSAGES[classify(error).type]
