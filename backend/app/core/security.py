"""Password hashing, JWT tokens and token fingerprints.

No FastAPI here: callers turn a None or False result into the HTTP answer.
"""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import settings

PASSWORD_RESET_EXPIRE_HOURS = 24


def _secret() -> str:
    return settings.jwt_secret_key.get_secret_value()


def _now() -> datetime:
    return datetime.now(UTC)


# --- Passwords -------------------------------------------------------------


def get_password_hash(password: str) -> str:
    """Hash a password with bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a password against its bcrypt hash. Never raises."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("ascii"))
    except (ValueError, TypeError):
        # Malformed hash, or a password bcrypt refuses (over 72 bytes).
        return False


# --- Stored token fingerprints ---------------------------------------------


def hash_token(token: str) -> str:
    """SHA-256 of a token, as stored in user_sessions instead of the token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _password_fingerprint(password_hash: str) -> str:
    """A short digest of the current password hash.

    Embedded in a password-reset token: once the password changes, the
    fingerprint no longer matches and the token stops working. That makes the
    token single-use without storing it.
    """
    return hashlib.sha256(password_hash.encode("utf-8")).hexdigest()[:32]


# --- JWT -------------------------------------------------------------------


def _encode(payload: dict) -> str:
    # A random "jti" makes every token unique. Without it a JWT is
    # deterministic: two tokens issued in the same second for the same user
    # were identical, so a rotated refresh token stayed valid and two logins in
    # one second collided on the unique access-token column.
    return jwt.encode(
        {**payload, "jti": secrets.token_urlsafe(16)}, _secret(), algorithm=settings.jwt_algorithm
    )


def decode_token(token: str) -> dict | None:
    """Decode and verify a JWT (signature and expiry). None if invalid."""
    if not token:
        return None
    try:
        return jwt.decode(token, _secret(), algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None


def verify_token(token: str, token_type: str = "access") -> dict | None:
    """Decode a JWT and check its type ("access" or "refresh")."""
    payload = decode_token(token)
    if payload and payload.get("type") == token_type:
        return payload
    return None


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    expire = _now() + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    return _encode({**data, "exp": expire, "type": "access"})


def create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT refresh token."""
    expire = _now() + (expires_delta or timedelta(days=settings.refresh_token_expire_days))
    return _encode({**data, "exp": expire, "type": "refresh"})


def create_tokens(user_id: int, email: str, role: str) -> dict:
    """Create both access and refresh tokens for a user."""
    token_data = {"sub": str(user_id), "email": email, "role": role}
    return {
        "access_token": create_access_token(token_data),
        "refresh_token": create_refresh_token(token_data),
        "token_type": "bearer",
    }


def refresh_token_expiry() -> datetime:
    """When a refresh token created now expires (stored with the session)."""
    return _now() + timedelta(days=settings.refresh_token_expire_days)


def create_password_reset_token(email: str, password_hash: str) -> str:
    """Create a single-use password reset token (see _password_fingerprint)."""
    return _encode(
        {
            "email": email,
            "fp": _password_fingerprint(password_hash),
            "type": "password_reset",
            "exp": _now() + timedelta(hours=PASSWORD_RESET_EXPIRE_HOURS),
        }
    )


def read_password_reset_token(token: str) -> dict | None:
    """Return the token's {"email", "fp"} if it is a valid reset token."""
    payload = decode_token(token)
    if not payload or payload.get("type") != "password_reset":
        return None
    if not payload.get("email") or not payload.get("fp"):
        return None
    return {"email": payload["email"], "fp": payload["fp"]}


def reset_token_matches(token_fingerprint: str, password_hash: str) -> bool:
    """True if the reset token was issued for the current password."""
    return hmac.compare_digest(token_fingerprint, _password_fingerprint(password_hash))
