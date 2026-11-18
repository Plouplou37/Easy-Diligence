"""
Shared validation utilities for the application.
"""

import re


def validate_password_strength(password: str) -> str:
    """
    Validate password strength according to application requirements.

    Requirements:
    - At least 8 characters long
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    - Contains at least one digit
    - At most 72 bytes once encoded: bcrypt reads no further, and would
      otherwise compare only the start of a longer password

    Args:
        password: The password string to validate

    Returns:
        The validated password string

    Raises:
        ValueError: If password doesn't meet requirements
    """
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")

    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password must be at most 72 bytes long")

    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")

    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")

    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit")

    return password
