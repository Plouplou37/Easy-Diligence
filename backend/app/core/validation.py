"""Password rules, shared by registration, password change and reset."""

import re

# bcrypt only reads the first 72 bytes of a password, and bcrypt >= 5 refuses
# longer ones outright: capping the length means a password is never silently cut.
BCRYPT_MAX_PASSWORD_BYTES = 72


def validate_password_strength(password: str) -> str:
    """Return the password if it is strong enough, raise ValueError otherwise.

    At least 8 characters, at most 72 bytes once encoded, with an uppercase
    letter, a lowercase letter and a digit.
    """
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")

    if len(password.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError(f"Password must be at most {BCRYPT_MAX_PASSWORD_BYTES} bytes long")

    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")

    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")

    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit")

    return password
