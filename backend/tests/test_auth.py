import pytest
from httpx import AsyncClient

from app.core.security import create_access_token, get_password_hash, verify_password, verify_token


class TestAuthentication:
    """Test authentication functionality."""

    @pytest.mark.unit
    def test_password_hashing(self):
        """Test password hashing and verification."""
        password = "testpassword123"
        hashed = get_password_hash(password)

        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("wrongpassword", hashed) is False

    @pytest.mark.unit
    def test_token_creation_and_verification(self):
        """Test JWT token creation and verification."""
        user_id = 123
        token = create_access_token(data={"sub": str(user_id)})

        assert token is not None
        assert isinstance(token, str)

        # Verify token
        payload = verify_token(token, token_type="access")
        assert payload is not None
        assert payload.get("sub") == str(user_id)

    @pytest.mark.unit
    def test_invalid_token_verification(self):
        """Test verification of invalid tokens."""
        invalid_token = "invalid.jwt.token"
        payload = verify_token(invalid_token, token_type="access")
        assert payload is None

    @pytest.mark.api
    async def test_login_endpoint_success(self, async_client: AsyncClient, create_test_user):
        """Test successful login."""
        user = create_test_user(email="test@example.com", password="testpass123")

        response = await async_client.post(
            "/api/auth/login", data={"username": user.email, "password": "testpass123"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.api
    async def test_login_endpoint_invalid_credentials(self, async_client: AsyncClient):
        """Test login with invalid credentials."""
        response = await async_client.post(
            "/api/auth/login", data={"username": "nonexistent@example.com", "password": "wrongpass"}
        )

        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

    @pytest.mark.api
    async def test_register_endpoint_success(self, async_client: AsyncClient):
        """Test successful user registration."""
        user_data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "newpass123",
        }

        response = await async_client.post("/api/auth/register", json=user_data)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["username"] == user_data["username"]
        assert "id" in data

    @pytest.mark.api
    async def test_register_duplicate_email(self, async_client: AsyncClient, create_test_user):
        """Test registration with duplicate email."""
        create_test_user(email="existing@example.com")

        user_data = {
            "email": "existing@example.com",
            "username": "newuser",
            "password": "newpass123",
        }

        response = await async_client.post("/api/auth/register", json=user_data)
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]
