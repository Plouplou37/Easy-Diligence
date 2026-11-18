import pytest

from app.core.security import get_password_hash, verify_password
from app.core.utils import generate_unique_code, validate_email
from app.models.company import Company
from app.models.user import User


class TestUtilityFunctions:
    """Test core utility functions."""

    @pytest.mark.unit
    def test_validate_email(self):
        """Test email validation function."""
        # Valid emails
        assert validate_email("test@example.com") is True
        assert validate_email("user.name+tag@domain.co.uk") is True

        # Invalid emails
        assert validate_email("invalid-email") is False
        assert validate_email("@domain.com") is False
        assert validate_email("user@") is False
        assert validate_email("") is False

    @pytest.mark.unit
    def test_generate_unique_code(self):
        """Test unique code generation."""
        code1 = generate_unique_code("Test", 123)
        code2 = generate_unique_code("Test", 123)
        code3 = generate_unique_code("Different", 456)

        # Codes should be strings and not empty
        assert isinstance(code1, str)
        assert len(code1) > 0

        # Same inputs should produce different codes (due to random component)
        assert code1 != code2

        # Different inputs should produce different codes
        assert code1 != code3

    @pytest.mark.unit
    def test_password_security(self):
        """Test password hashing security."""
        password = "supersecretpassword123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        # Same password should produce different hashes (salt)
        assert hash1 != hash2

        # Both hashes should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True

        # Wrong password should not verify
        assert verify_password("wrongpassword", hash1) is False


class TestModelValidation:
    """Test model validation and constraints."""

    @pytest.mark.unit
    def test_user_model_creation(self, test_db):
        """Test User model creation and validation."""
        from tests.conftest import TestingSessionLocal

        db = TestingSessionLocal()

        user = User(
            email="model@test.com",
            username="modeluser",
            hashed_password=get_password_hash("testpass"),
            role="user",
            is_active=True,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        assert user.id is not None
        assert user.email == "model@test.com"
        assert user.username == "modeluser"
        assert user.role == "user"
        assert user.is_active is True
        assert user.created_at is not None

        db.close()

    @pytest.mark.unit
    def test_company_model_creation(self, test_db):
        """Test Company model creation and validation."""
        from tests.conftest import TestingSessionLocal

        db = TestingSessionLocal()

        company = Company(
            name="Model Test Company",
            website_url="https://modeltest.com",
            description="Testing company model",
        )

        db.add(company)
        db.commit()
        db.refresh(company)

        assert company.id is not None
        assert company.name == "Model Test Company"
        assert company.website_url == "https://modeltest.com"
        assert company.description == "Testing company model"
        assert company.created_at is not None
        assert company.updated_at is not None

        db.close()


class TestDatabaseConstraints:
    """Test database constraints and validations."""

    @pytest.mark.db
    def test_unique_email_constraint(self, test_db):
        """Test that duplicate emails are prevented."""
        from sqlalchemy.exc import IntegrityError

        from tests.conftest import TestingSessionLocal

        db = TestingSessionLocal()

        # Create first user
        user1 = User(
            email="unique@test.com",
            username="user1",
            hashed_password=get_password_hash("pass1"),
            role="user",
            is_active=True,
        )
        db.add(user1)
        db.commit()

        # Try to create second user with same email
        user2 = User(
            email="unique@test.com",  # Same email
            username="user2",
            hashed_password=get_password_hash("pass2"),
            role="user",
            is_active=True,
        )
        db.add(user2)

        with pytest.raises(IntegrityError):
            db.commit()

        db.close()

    @pytest.mark.db
    def test_company_name_required(self, test_db):
        """Test that company name is required."""
        from sqlalchemy.exc import IntegrityError

        from tests.conftest import TestingSessionLocal

        db = TestingSessionLocal()

        company = Company(
            name=None,  # Missing required field
            website_url="https://test.com",
        )

        db.add(company)

        with pytest.raises(IntegrityError):
            db.commit()

        db.close()
