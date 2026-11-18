"""
Tests to validate Company Management Security fixes
Ensures all company endpoints have authentication and audit fields are populated
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.company import Company
from app.models.user import User


class TestCompanyEndpointAuthentication:
    """Test that all company endpoints require authentication"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_create_company_requires_auth(self, client):
        """Test that creating a company requires authentication"""
        # Request without authentication
        company_data = {
            "name": "Test Company",
            "website_url": "https://test.com",
            "description": "Test description",
        }

        response = client.post("/api/company/", json=company_data)

        # Should return 401 or similar auth error
        assert response.status_code in [401, 403, 422], (
            f"Expected auth error, got {response.status_code}"
        )

    def test_list_companies_requires_auth(self, client):
        """Test that listing companies requires authentication"""
        response = client.get("/api/company/")

        # Should return 401 or similar auth error
        assert response.status_code in [401, 403, 422], (
            f"Expected auth error, got {response.status_code}"
        )

    def test_get_company_requires_auth(self, client):
        """Test that getting a company requires authentication"""
        response = client.get("/api/company/1")

        # Should return 401 or similar auth error
        assert response.status_code in [401, 403, 422], (
            f"Expected auth error, got {response.status_code}"
        )

    def test_update_company_requires_auth(self, client):
        """Test that updating a company requires authentication"""
        company_data = {
            "name": "Updated Company",
            "website_url": "https://updated.com",
            "description": "Updated description",
        }

        response = client.put("/api/company/1", json=company_data)

        # Should return 401 or similar auth error
        assert response.status_code in [401, 403, 422], (
            f"Expected auth error, got {response.status_code}"
        )


class TestCompanyAuditFields:
    """Test that company audit fields are populated correctly"""

    def test_company_model_has_audit_fields(self):
        """Test that Company model has all required audit fields"""
        # Check that audit fields exist
        assert hasattr(Company, "created_by"), "Company should have created_by field"
        assert hasattr(Company, "updated_by"), "Company should have updated_by field"
        assert hasattr(Company, "created_at"), "Company should have created_at field"
        assert hasattr(Company, "updated_at"), "Company should have updated_at field"

    def test_company_model_audit_relationships(self):
        """Test that Company model has audit relationships"""
        # Check relationships exist
        assert hasattr(Company, "creator"), "Company should have creator relationship"
        assert hasattr(Company, "updater"), "Company should have updater relationship"

    @patch("app.api.routes.company.get_db")
    @patch("app.api.routes.company.get_current_active_user")
    def test_create_company_populates_created_by(self, mock_user, mock_db):
        """Test that creating a company populates created_by field"""
        from app.api.routes.company import create_company
        from app.schemas.company import CompanyCreate

        # Mock user
        mock_user.return_value = MagicMock()
        mock_user.return_value.id = 123

        # Mock database
        mock_db_session = MagicMock(spec=Session)
        mock_db.return_value = mock_db_session

        # Mock company creation
        company_data = CompanyCreate(
            name="Test Company", website_url="https://test.com", description="Test description"
        )

        # Call the function
        create_company(
            company=company_data, db=mock_db_session, current_user=mock_user.return_value
        )

        # Verify that a Company was added to the database
        mock_db_session.add.assert_called_once()
        added_company = mock_db_session.add.call_args[0][0]

        # Check that created_by was set
        assert added_company.created_by == 123, (
            f"Expected created_by=123, got {added_company.created_by}"
        )

        # Check other fields
        assert added_company.name == "Test Company"
        assert added_company.website_url == "https://test.com"
        assert added_company.description == "Test description"

    @patch("app.api.routes.company.get_db")
    @patch("app.api.routes.company.get_current_active_user")
    def test_update_company_populates_updated_by(self, mock_user, mock_db):
        """Test that updating a company populates updated_by field"""
        from app.api.routes.company import update_company
        from app.schemas.company import CompanyCreate

        # Mock user
        mock_user.return_value = MagicMock()
        mock_user.return_value.id = 456

        # Mock existing company
        mock_company = MagicMock(spec=Company)
        mock_company.id = 1
        mock_company.name = "Old Name"
        mock_company.website_url = "https://old.com"
        mock_company.description = "Old description"

        # Mock database
        mock_db_session = MagicMock(spec=Session)
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_company
        mock_db.return_value = mock_db_session

        # Mock company update data
        update_data = CompanyCreate(
            name="Updated Company",
            website_url="https://updated.com",
            description="Updated description",
        )

        # Call the function
        update_company(
            company_id=1,
            company_update=update_data,
            db=mock_db_session,
            current_user=mock_user.return_value,
        )

        # Check that updated_by was set
        assert mock_company.updated_by == 456, (
            f"Expected updated_by=456, got {mock_company.updated_by}"
        )

        # Check that other fields were updated
        assert mock_company.name == "Updated Company"
        assert mock_company.website_url == "https://updated.com"
        assert mock_company.description == "Updated description"


class TestCompanySecurityValidation:
    """Test overall company security validation"""

    def test_company_endpoints_exist(self):
        """Test that company endpoints are properly defined"""
        from app.api.routes.company import router

        # Get all routes
        routes = router.routes
        route_paths = [route.path for route in routes]
        route_methods = []

        for route in routes:
            if hasattr(route, "methods"):
                route_methods.extend([(route.path, method) for method in route.methods])

        # Check expected endpoints exist
        expected_endpoints = [
            ("/", "POST"),  # create company
            ("/", "GET"),  # list companies
            ("/{company_id}", "GET"),  # get company
            ("/{company_id}", "PUT"),  # update company
        ]

        for path, method in expected_endpoints:
            endpoint_exists = any(
                route_path == path and (route_path, method) in route_methods
                for route_path in route_paths
            )
            assert endpoint_exists, f"Expected endpoint {method} {path} not found"

    def test_company_authentication_dependencies(self):
        """Test that company endpoints have authentication dependencies"""
        import inspect

        from app.api.routes.company import router

        # Get all endpoint functions
        for route in router.routes:
            if hasattr(route, "endpoint") and route.endpoint:
                endpoint_func = route.endpoint

                # Skip non-company endpoints (like auth-test)
                if "company" not in endpoint_func.__name__.lower():
                    continue

                # Get function signature
                signature = inspect.signature(endpoint_func)

                # Check if current_user parameter exists
                has_auth = any(
                    param.annotation == User
                    and str(param.default).find("get_current_active_user") != -1
                    for param in signature.parameters.values()
                )

                assert has_auth, f"Endpoint {endpoint_func.__name__} missing authentication"

    def test_company_model_foreign_key_constraints(self):
        """Test that company model has proper foreign key constraints"""
        # Check created_by foreign key
        created_by_column = Company.__table__.columns["created_by"]
        assert created_by_column.foreign_keys, "created_by should have foreign key constraint"

        created_by_fk = list(created_by_column.foreign_keys)[0]
        assert str(created_by_fk.column) == "users.id", (
            f"created_by should reference users.id, got {created_by_fk.column}"
        )

        # Check updated_by foreign key
        updated_by_column = Company.__table__.columns["updated_by"]
        assert updated_by_column.foreign_keys, "updated_by should have foreign key constraint"

        updated_by_fk = list(updated_by_column.foreign_keys)[0]
        assert str(updated_by_fk.column) == "users.id", (
            f"updated_by should reference users.id, got {updated_by_fk.column}"
        )

    def test_company_audit_fields_nullable(self):
        """Test that audit fields have correct nullable settings"""
        # created_by and updated_by should be nullable (for flexibility)
        created_by_column = Company.__table__.columns["created_by"]
        assert created_by_column.nullable, "created_by should be nullable"

        updated_by_column = Company.__table__.columns["updated_by"]
        assert updated_by_column.nullable, "updated_by should be nullable"

        # Timestamps should not be nullable
        created_at_column = Company.__table__.columns["created_at"]
        assert not created_at_column.nullable, "created_at should not be nullable"

        updated_at_column = Company.__table__.columns["updated_at"]
        assert not updated_at_column.nullable, "updated_at should not be nullable"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
