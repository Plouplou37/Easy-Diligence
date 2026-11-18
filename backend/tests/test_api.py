import pytest
from httpx import AsyncClient

from app.core.security import create_access_token


class TestCompanyAPI:
    """Test Company API endpoints."""

    async def get_auth_headers(self, user_id: int):
        """Get authentication headers for API calls."""
        token = create_access_token(data={"sub": str(user_id)})
        return {"Authorization": f"Bearer {token}"}

    @pytest.mark.api
    @pytest.mark.auth
    async def test_create_company_without_auth(self, async_client: AsyncClient):
        """Test creating company without authentication fails."""
        company_data = {
            "name": "Unauthorized Company",
            "website_url": "https://test.com",
            "description": "Should fail",
        }

        response = await async_client.post("/api/company/", json=company_data)
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

    @pytest.mark.api
    async def test_create_company_with_auth(
        self, async_client: AsyncClient, create_test_user, test_company_data
    ):
        """Test creating company with authentication succeeds."""
        user = create_test_user()
        headers = await self.get_auth_headers(user.id)

        response = await async_client.post("/api/company/", json=test_company_data, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == test_company_data["name"]
        assert data["website_url"] == test_company_data["website_url"]
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.api
    @pytest.mark.auth
    async def test_list_companies_without_auth(self, async_client: AsyncClient):
        """Test listing companies without authentication fails."""
        response = await async_client.get("/api/company/")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

    @pytest.mark.api
    async def test_list_companies_with_auth(
        self, async_client: AsyncClient, create_test_user, create_test_company
    ):
        """Test listing companies with authentication succeeds."""
        user = create_test_user()
        company = create_test_company()
        headers = await self.get_auth_headers(user.id)

        response = await async_client.get("/api/company/", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["id"] == company.id

    @pytest.mark.api
    async def test_get_company_by_id(
        self, async_client: AsyncClient, create_test_user, create_test_company
    ):
        """Test getting specific company by ID."""
        user = create_test_user()
        company = create_test_company(name="Specific Company")
        headers = await self.get_auth_headers(user.id)

        response = await async_client.get(f"/api/company/{company.id}", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == company.id
        assert data["name"] == "Specific Company"

    @pytest.mark.api
    async def test_get_nonexistent_company(self, async_client: AsyncClient, create_test_user):
        """Test getting non-existent company returns 404."""
        user = create_test_user()
        headers = await self.get_auth_headers(user.id)

        response = await async_client.get("/api/company/99999", headers=headers)

        assert response.status_code == 404
        assert "Company not found" in response.json()["detail"]

    @pytest.mark.api
    async def test_update_company(
        self, async_client: AsyncClient, create_test_user, create_test_company
    ):
        """Test updating company information."""
        user = create_test_user()
        company = create_test_company()
        headers = await self.get_auth_headers(user.id)

        update_data = {
            "name": "Updated Company Name",
            "website_url": "https://updated.com",
            "description": "Updated description",
        }

        response = await async_client.put(
            f"/api/company/{company.id}", json=update_data, headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["website_url"] == update_data["website_url"]
        assert data["description"] == update_data["description"]

    @pytest.mark.api
    @pytest.mark.auth
    async def test_auth_test_endpoint(self, async_client: AsyncClient, create_test_user):
        """Test the auth test endpoint."""
        user = create_test_user(email="authtest@example.com")
        headers = await self.get_auth_headers(user.id)

        response = await async_client.get("/api/company/auth-test", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Authentication working"
        assert data["user"] == user.email


class TestHealthEndpoints:
    """Test basic health and status endpoints."""

    @pytest.mark.api
    async def test_root_endpoint(self, async_client: AsyncClient):
        """Test root endpoint."""
        response = await async_client.get("/")
        assert response.status_code == 200
        assert response.json()["message"] == "Due Diligence Automation API"

    @pytest.mark.api
    async def test_health_endpoint(self, async_client: AsyncClient):
        """Test health check endpoint."""
        response = await async_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
