"""Password hashing and JWT helpers (core/security.py)."""

from datetime import timedelta

from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    verify_token,
)


def test_password_hash_verifies_only_the_right_password():
    hashed = get_password_hash("Str0ngPassw0rd")
    assert hashed != "Str0ngPassw0rd"
    assert verify_password("Str0ngPassw0rd", hashed)
    assert not verify_password("wrong-password", hashed)


def test_same_password_gets_a_different_salt():
    first, second = get_password_hash("Same-Passw0rd"), get_password_hash("Same-Passw0rd")
    assert first != second
    assert verify_password("Same-Passw0rd", first) and verify_password("Same-Passw0rd", second)


def test_malformed_hash_is_refused_without_raising():
    assert not verify_password("anything", "not-a-bcrypt-hash")


def test_access_token_round_trip():
    payload = verify_token(create_access_token({"sub": "42"}), token_type="access")
    assert payload is not None and payload["sub"] == "42"


def test_token_type_is_checked():
    refresh = create_refresh_token({"sub": "42"})
    assert verify_token(refresh, token_type="access") is None
    assert verify_token(refresh, token_type="refresh") is not None


def test_expired_token_is_refused():
    token = create_access_token({"sub": "42"}, expires_delta=timedelta(seconds=-1))
    assert verify_token(token, token_type="access") is None


def test_invalid_tokens_are_refused():
    for token in ["invalid.token.here", "not.a.token", "", None, "eyJhbGciOiJIUzI1NiJ9.invalid"]:
        assert verify_token(token, token_type="access") is None


def test_two_tokens_issued_together_differ():
    # Each token carries a random jti: identical tokens broke refresh rotation.
    assert create_access_token({"sub": "42"}) != create_access_token({"sub": "42"})
