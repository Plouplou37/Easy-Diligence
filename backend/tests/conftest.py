from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import get_password_hash
from app.main import app
from app.models.company import Company
from app.models.user import User

# Test database setup. A file (ignored by git), not memory: some tests import
# this module a second time as tests.conftest, and must reach the same tables.
# The event loop comes from pytest-asyncio (asyncio_mode = "auto" in pyproject.toml).
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def test_db():
    """Create test database tables and clean up after test."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def override_get_db():
    """Override get_db dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture
async def async_client(test_db):
    """Create async HTTP client for API testing."""
    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def test_user_data():
    """Test user data fixture."""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpass123",
        "role": "user",
    }


@pytest.fixture
def test_admin_data():
    """Test admin user data fixture."""
    return {
        "email": "admin@example.com",
        "username": "admin",
        "password": "adminpass123",
        "role": "admin",
    }


@pytest.fixture
def test_company_data():
    """Test company data fixture."""
    return {
        "name": "Test Company",
        "website_url": "https://testcompany.com",
        "description": "A test company for unit testing",
    }


@pytest.fixture
def create_test_user(test_db):
    """Create a test user in the database."""
    db = TestingSessionLocal()

    def _create_user(email="test@example.com", password="testpass123", role="user"):
        hashed_password = get_password_hash(password)
        user = User(
            email=email,
            username=email.split("@")[0],
            hashed_password=hashed_password,
            role=role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    yield _create_user
    db.close()


@pytest.fixture
def create_test_company(test_db):
    """Create a test company in the database."""
    db = TestingSessionLocal()

    def _create_company(name="Test Company", website_url="https://test.com"):
        company = Company(name=name, website_url=website_url, description="Test company")
        db.add(company)
        db.commit()
        db.refresh(company)
        return company

    yield _create_company
    db.close()


@pytest.fixture
def mock_redis():
    """Mock Redis for testing."""
    with patch("redis.from_url") as mock:
        yield mock


@pytest.fixture
def mock_openai():
    """Mock OpenAI client for testing."""
    with patch("app.engine.openai_client.openai_client") as mock:
        yield mock
