"""How the engine reads an error (engine/errors.py): by the class the OpenAI SDK
raises, never by its text. One case per line of the table."""

import httpx
import openai
import pytest

from app.engine.errors import (
    MAX_DELAY,
    MESSAGES,
    Failure,
    ResponseError,
    classify,
    is_global,
    retry_delay,
)
from app.engine.openai_client import OpenAIProcessor
from app.models.answer import ErrorType

REQUEST = httpx.Request("POST", "https://api.openai.com/v1/responses")


def status_error(cls, status, headers=None, **body):
    response = httpx.Response(status, request=REQUEST, headers=headers)
    return cls("invalid request", response=response, body=body or None)


@pytest.mark.parametrize(
    ("error", "error_type", "retryable"),
    [
        (status_error(openai.RateLimitError, 429), ErrorType.RATE_LIMIT, True),
        (openai.APITimeoutError(REQUEST), ErrorType.TIMEOUT, True),
        (openai.APIConnectionError(request=REQUEST), ErrorType.NETWORK_ERROR, True),
        (
            status_error(openai.BadRequestError, 400, code="context_length_exceeded"),
            ErrorType.CONTEXT_OVERFLOW,
            False,
        ),
        (status_error(openai.BadRequestError, 400), ErrorType.VALIDATION_ERROR, False),
        (status_error(openai.UnprocessableEntityError, 422), ErrorType.VALIDATION_ERROR, False),
        (status_error(openai.AuthenticationError, 401), ErrorType.API_ERROR, False),
        (status_error(openai.PermissionDeniedError, 403), ErrorType.API_ERROR, False),
        (status_error(openai.InternalServerError, 500), ErrorType.API_ERROR, True),
        (status_error(openai.APIStatusError, 503), ErrorType.API_ERROR, True),
        (ResponseError("OpenAI response not completed"), ErrorType.API_ERROR, True),
        # The text no longer decides: "invalid" made this a validation error.
        (ValueError("invalid value"), ErrorType.UNKNOWN, True),
        (status_error(openai.NotFoundError, 404), ErrorType.UNKNOWN, True),
    ],
)
def test_each_error_has_its_type_and_its_retry(error, error_type, retryable):
    assert classify(error) == Failure(error_type, retryable)


def test_what_every_question_would_meet_is_global():
    assert [t for t in ErrorType if is_global(t)] == [
        ErrorType.RATE_LIMIT,
        ErrorType.API_ERROR,
        ErrorType.NETWORK_ERROR,
    ]


def test_the_delay_follows_retry_after_or_backs_off():
    rate_limit = Failure(ErrorType.RATE_LIMIT, True)
    asked = status_error(openai.RateLimitError, 429, headers={"retry-after": "7"})
    assert retry_delay(asked, rate_limit, 0) == 7.0
    asked_ms = status_error(openai.RateLimitError, 429, headers={"retry-after-ms": "1500"})
    assert retry_delay(asked_ms, rate_limit, 0) == 1.5
    too_long = status_error(openai.RateLimitError, 429, headers={"retry-after": "3600"})
    assert retry_delay(too_long, rate_limit, 0) == MAX_DELAY

    silent = status_error(openai.RateLimitError, 429)
    assert [retry_delay(silent, rate_limit, n) for n in range(3)] == [5.0, 10.0, 20.0]
    unknown = Failure(ErrorType.UNKNOWN, True)
    assert retry_delay(ValueError(), unknown, 10) == MAX_DELAY


def test_every_type_has_a_message_for_the_user():
    assert set(MESSAGES) == set(ErrorType)


def test_the_sdk_does_not_retry_on_its_own():
    """One retry policy, the engine's: the SDK used to retry twice more under
    each of its attempts, up to nine calls for one question."""
    assert OpenAIProcessor().client.max_retries == 0
