"""Helpers of core/utils.py."""

import pytest

from app.core.utils import generate_unique_code, validate_email


@pytest.mark.parametrize(
    "email",
    [
        "test@example.com",
        "user.name@domain.co.uk",
        "user+tag@example.net",
        "firstname.lastname@company.org",
        "user123@test-domain.com",
    ],
)
def test_valid_emails(email):
    assert validate_email(email) is True


@pytest.mark.parametrize(
    "email",
    [
        "invalid-email",
        "@domain.com",
        "user@",
        "user@domain",
        "",
        None,
        "user space@domain.com",
        "user@domain.",
        ".user@domain.com",
    ],
)
def test_invalid_emails(email):
    assert validate_email(email) is False


def test_unique_code_format():
    prefix, user, suffix = generate_unique_code("Test Project", 42).split("-")
    assert prefix == "TES"
    assert user == "42"
    assert len(suffix) == 4


def test_unique_code_differs_for_the_same_input():
    first, second = generate_unique_code("Same Name", 123), generate_unique_code("Same Name", 123)
    assert first != second
    assert first.split("-")[:2] == second.split("-")[:2]


@pytest.mark.parametrize(
    ("name", "prefix"),
    [
        ("", "GEN-"),
        ("This is a very long project name that exceeds normal limits", "THI-"),
        ("My Project! @#$", "MYP-"),
    ],
)
def test_unique_code_prefix_edge_cases(name, prefix):
    assert generate_unique_code(name, 1).startswith(prefix)
