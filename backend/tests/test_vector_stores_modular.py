"""
Test suite for modularized vector stores API
Validates that all functionality works after breaking down the large file
"""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.session import DDSession
from app.models.user import User
from app.models.vector_store import VectorStore


class TestVectorStoreCoreModule:
    """Test the core CRUD operations module"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def mock_db(self):
        db = MagicMock(spec=Session)
        return db

    @pytest.fixture
    def mock_user(self):
        user = User(id=1, email="test@example.com", username="testuser", role="user")
        return user

    @pytest.fixture
    def mock_vector_store(self):
        return VectorStore(
            id="vs_123456789",
            name="Test Store",
            description="Test Description",
            created_by=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

    @patch('app.api.routes.vector_stores.core.OpenAIProcessor')
    @patch('app.api.routes.vector_stores.core.get_db')
    @patch('app.api.deps.get_current_active_user')
    def test_list_vector_stores(self, mock_auth, mock_db_dep, mock_openai, client, mock_db, mock_user, mock_vector_store):
        """Test listing vector stores with OpenAI enrichment"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_db_dep.return_value = mock_db
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_vector_store]

        mock_openai_instance = AsyncMock()
        mock_openai_instance.get_vector_store.return_value = {
            "file_counts": {"total": 5},
            "status": "completed",
            "usage_bytes": 1024
        }
        mock_openai.return_value = mock_openai_instance

        # Make request
        response = client.get("/vector-stores/")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "vs_123456789"
        assert data[0]["name"] == "Test Store"
        assert data[0]["file_count"] == 5
        assert data[0]["status"] == "completed"
        assert data[0]["total_bytes"] == 1024

    @patch('app.api.routes.vector_stores.core.OpenAIProcessor')
    @patch('app.api.routes.vector_stores.core.get_db')
    @patch('app.api.deps.get_current_active_user')
    def test_create_vector_store(self, mock_auth, mock_db_dep, mock_openai, client, mock_db, mock_user):
        """Test creating a new vector store"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_db_dep.return_value = mock_db

        mock_openai_instance = AsyncMock()
        mock_openai_instance.create_vector_store.return_value = {"id": "vs_new123456"}
        mock_openai.return_value = mock_openai_instance

        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        # Mock the created vector store
        VectorStore(
            id="vs_new123456",
            name="New Store",
            description="New Description",
            created_by=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        mock_db.refresh.side_effect = lambda obj: setattr(obj, 'id', 'vs_new123456')

        # Make request
        response = client.post("/vector-stores/", json={
            "name": "New Store",
            "description": "New Description"
        })

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "vs_new123456"
        assert data["name"] == "New Store"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @patch('app.api.routes.vector_stores.core.OpenAIProcessor')
    @patch('app.api.routes.vector_stores.core.get_db')
    @patch('app.api.deps.get_current_active_user')
    def test_get_vector_store(self, mock_auth, mock_db_dep, mock_openai, client, mock_db, mock_user, mock_vector_store):
        """Test getting a specific vector store"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_db_dep.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = mock_vector_store

        mock_openai_instance = AsyncMock()
        mock_openai_instance.get_vector_store.return_value = {
            "file_counts": {"total": 3},
            "status": "completed",
            "usage_bytes": 512
        }
        mock_openai.return_value = mock_openai_instance

        # Make request
        response = client.get("/vector-stores/vs_123456789")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "vs_123456789"
        assert data["file_count"] == 3
        assert data["total_bytes"] == 512

    @patch('app.api.routes.vector_stores.core.get_db')
    @patch('app.api.deps.get_current_active_user')
    def test_get_vector_store_not_found(self, mock_auth, mock_db_dep, client, mock_db, mock_user):
        """Test getting a non-existent vector store"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_db_dep.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Make request
        response = client.get("/vector-stores/vs_nonexistent")

        # Assertions
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @patch('app.api.routes.vector_stores.core.OpenAIProcessor')
    @patch('app.api.routes.vector_stores.core.get_db')
    @patch('app.api.deps.get_current_active_user')
    def test_update_vector_store(self, mock_auth, mock_db_dep, mock_openai, client, mock_db, mock_user, mock_vector_store):
        """Test updating a vector store"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_db_dep.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = mock_vector_store

        mock_openai_instance = AsyncMock()
        mock_openai_instance.modify_vector_store.return_value = {"id": "vs_123456789"}
        mock_openai_instance.get_vector_store.return_value = {
            "file_counts": {"total": 0},
            "status": "completed",
            "usage_bytes": 0
        }
        mock_openai.return_value = mock_openai_instance

        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        # Make request
        response = client.patch("/vector-stores/vs_123456789", json={
            "name": "Updated Store Name",
            "description": "Updated Description"
        })

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Store Name"
        mock_db.commit.assert_called_once()

    @patch('app.api.routes.vector_stores.core.OpenAIProcessor')
    @patch('app.api.routes.vector_stores.core.get_db')
    @patch('app.api.deps.get_current_active_user')
    def test_delete_vector_store(self, mock_auth, mock_db_dep, mock_openai, client, mock_db, mock_user, mock_vector_store):
        """Test deleting a vector store"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_db_dep.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = mock_vector_store
        mock_db.query.return_value.filter.return_value.delete.return_value = 1

        mock_openai_instance = AsyncMock()
        mock_openai_instance.delete_vector_store.return_value = {"deleted": True}
        mock_openai.return_value = mock_openai_instance

        mock_db.delete = MagicMock()
        mock_db.commit = MagicMock()

        # Make request
        response = client.delete("/vector-stores/vs_123456789")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data["message"]
        mock_db.delete.assert_called_once_with(mock_vector_store)
        mock_db.commit.assert_called_once()


class TestVectorStoreFilesModule:
    """Test the file management module"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def mock_db(self):
        db = MagicMock(spec=Session)
        return db

    @pytest.fixture
    def mock_user(self):
        return User(id=1, email="test@example.com", username="testuser", role="user")

    @pytest.fixture
    def mock_vector_store(self):
        return VectorStore(
            id="vs_123456789",
            name="Test Store",
            created_by=1,
            created_at=datetime.utcnow()
        )

    @patch('app.api.routes.vector_stores.files.OpenAIProcessor')
    @patch('app.api.routes.vector_stores.files.get_db')
    @patch('app.api.deps.get_current_active_user')
    def test_list_vector_store_files(self, mock_auth, mock_db_dep, mock_openai, client, mock_db, mock_user, mock_vector_store):
        """Test listing files in a vector store"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_db_dep.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = mock_vector_store

        mock_openai_instance = AsyncMock()
        mock_openai_instance.list_vector_store_files.return_value = [
            {"id": "file_123", "filename": "test.pdf", "bytes": 1024}
        ]
        mock_openai.return_value = mock_openai_instance

        # Make request
        response = client.get("/vector-stores/vs_123456789/files")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "files" in data
        assert len(data["files"]) == 1
        assert data["files"][0]["id"] == "file_123"

    @patch('app.api.routes.vector_stores.files.OpenAIProcessor')
    @patch('app.api.routes.vector_stores.files.get_db')
    @patch('app.api.deps.get_current_active_user')
    def test_upload_file_to_vector_store(self, mock_auth, mock_db_dep, mock_openai, client, mock_db, mock_user, mock_vector_store):
        """Test uploading a file to a vector store"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_db_dep.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = mock_vector_store

        mock_openai_instance = AsyncMock()
        mock_openai_instance.upload_file.return_value = "file_123"
        mock_openai_instance.add_file_to_vector_store.return_value = {"id": "vs_file_123"}
        mock_openai.return_value = mock_openai_instance

        # Create mock file
        file_content = b"Test file content"

        # Make request
        response = client.post(
            "/vector-stores/vs_123456789/files",
            files={"file": ("test.txt", file_content, "text/plain")}
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["file_id"] == "file_123"
        assert data["filename"] == "test.txt"
        assert data["status"] == "uploaded"

    @patch('app.api.routes.vector_stores.files.OpenAIProcessor')
    @patch('app.api.routes.vector_stores.files.get_db')
    @patch('app.api.deps.get_current_active_user')
    def test_delete_file_from_vector_store(self, mock_auth, mock_db_dep, mock_openai, client, mock_db, mock_user, mock_vector_store):
        """Test deleting a file from a vector store"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_db_dep.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = mock_vector_store

        mock_openai_instance = AsyncMock()
        mock_openai_instance.remove_file_from_vector_store.return_value = {"deleted": True}
        mock_openai_instance.delete_file.return_value = {"deleted": True}
        mock_openai.return_value = mock_openai_instance

        # Make request
        response = client.delete("/vector-stores/vs_123456789/files/file_123")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data["message"]


class TestVectorStoreSessionsModule:
    """Test the session assignment module"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def mock_db(self):
        db = MagicMock(spec=Session)
        return db

    @pytest.fixture
    def mock_user(self):
        return User(id=1, email="test@example.com", username="testuser", role="user")

    @pytest.fixture
    def mock_session(self):
        return DDSession(
            id=1,
            name="Test Session",
            created_by=1,
            created_at=datetime.utcnow()
        )

    @pytest.fixture
    def mock_vector_store(self):
        return VectorStore(
            id="vs_123456789",
            name="Test Store",
            created_by=1,
            created_at=datetime.utcnow()
        )

    @patch('app.api.routes.vector_stores.sessions.get_db')
    @patch('app.api.deps.get_current_active_user')
    def test_get_session_vector_store_assignments(self, mock_auth, mock_db_dep, client, mock_db, mock_user, mock_session, mock_vector_store):
        """Test getting vector store assignments for a session"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_db_dep.return_value = mock_db

        # Mock session query
        mock_db.query.return_value.filter.return_value.first.return_value = mock_session

        # Mock assignments query
        mock_assignment = MagicMock()
        mock_assignment.assigned_at = datetime.utcnow()
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = [
            (mock_assignment, mock_vector_store)
        ]

        # Make request
        response = client.get("/vector-stores/session/1/assignments")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == 1
        assert data["session_name"] == "Test Session"
        assert len(data["assignments"]) == 1
        assert data["assignments"][0]["vector_store_id"] == "vs_123456789"

    @patch('app.api.routes.vector_stores.sessions.get_db')
    @patch('app.api.deps.get_current_active_user')
    def test_assign_vector_store_to_session(self, mock_auth, mock_db_dep, client, mock_db, mock_user, mock_session, mock_vector_store):
        """Test assigning a vector store to a session"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_db_dep.return_value = mock_db

        # Mock vector store and session queries
        mock_db.query.return_value.filter.return_value.first.side_effect = [mock_vector_store, mock_session]

        # Mock no existing assignment
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Mock database operations
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.execute.return_value.scalar.return_value = datetime.utcnow()

        # Make request
        response = client.put("/vector-stores/vs_123456789/assign-session/1")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "assigned to session successfully" in data["message"]
        assert data["assignment"]["vector_store_id"] == "vs_123456789"
        assert data["assignment"]["session_id"] == 1
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()


class TestVectorStoreSearchModule:
    """Test the search functionality module"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def mock_db(self):
        db = MagicMock(spec=Session)
        return db

    @pytest.fixture
    def mock_user(self):
        return User(id=1, email="test@example.com", username="testuser", role="user")

    @pytest.fixture
    def mock_vector_store(self):
        return VectorStore(
            id="vs_123456789",
            name="Test Store",
            created_by=1,
            created_at=datetime.utcnow()
        )

    @patch('app.api.routes.vector_stores.search.OpenAIProcessor')
    @patch('app.api.routes.vector_stores.search.get_db')
    @patch('app.api.deps.get_current_active_user')
    def test_search_vector_store(self, mock_auth, mock_db_dep, mock_openai, client, mock_db, mock_user, mock_vector_store):
        """Test searching within a vector store"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_db_dep.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = mock_vector_store

        mock_openai_instance = AsyncMock()
        mock_openai_instance.search_vector_store.return_value = {
            "results": [
                {"score": 0.95, "content": "Test result", "file_id": "file_123"}
            ],
            "processing_time_ms": 150
        }
        mock_openai.return_value = mock_openai_instance

        # Make request
        response = client.post("/vector-stores/vs_123456789/search", json={
            "query": "test search query",
            "limit": 10
        })

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "test search query"
        assert data["vector_store_id"] == "vs_123456789"
        assert len(data["results"]) == 1
        assert data["results"][0]["score"] == 0.95
        assert data["processing_time_ms"] == 150


class TestModularRouterIntegration:
    """Test that all modules are properly integrated"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_all_routes_available(self, client):
        """Test that all routes from all modules are available"""
        # Get OpenAPI schema to check available routes
        response = client.get("/openapi.json")
        assert response.status_code == 200

        openapi_data = response.json()
        paths = openapi_data["paths"]

        # Check that vector store routes exist
        vector_store_routes = [path for path in paths.keys() if path.startswith("/vector-stores")]

        # Should have routes from all modules
        expected_route_patterns = [
            "/vector-stores/",  # Core: list/create
            "/vector-stores/{vector_store_id}",  # Core: get/update/delete
            "/vector-stores/{vector_store_id}/files",  # Files: list/upload
            "/vector-stores/{vector_store_id}/files/{file_id}",  # Files: delete
            "/vector-stores/{vector_store_id}/assign-session/{session_identifier}",  # Sessions
            "/vector-stores/session/{session_identifier}/assignments",  # Sessions
            "/vector-stores/{vector_store_id}/search",  # Search
        ]

        for pattern in expected_route_patterns:
            assert any(pattern in route for route in vector_store_routes), f"Route pattern {pattern} not found"

    def test_route_tags_properly_assigned(self, client):
        """Test that routes have proper tags from modules"""
        response = client.get("/openapi.json")
        openapi_data = response.json()

        # Check that vector store routes have proper tags
        paths = openapi_data["paths"]

        # Find a core route and check its tags
        if "/vector-stores/" in paths:
            get_method = paths["/vector-stores/"].get("get")
            if get_method:
                tags = get_method.get("tags", [])
                assert any("vector-stores" in tag for tag in tags), "Core routes should have vector-stores tags"


if __name__ == "__main__":
    pytest.main([__file__])
