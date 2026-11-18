"""
Basic unit tests that don't require database setup.
These tests focus on pure functions and core logic.
"""
import pytest
from app.core.security import verify_password, get_password_hash, create_access_token, verify_token
from app.core.utils import validate_email, generate_unique_code


class TestSecurityFunctions:
    """Test security-related functions."""
    
    def test_password_hashing_and_verification(self):
        """Test password hashing and verification works correctly."""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        # Hash should be different from original password
        assert hashed != password
        assert len(hashed) > len(password)
        
        # Verification should work
        assert verify_password(password, hashed) is True
        assert verify_password("wrong_password", hashed) is False
    
    def test_password_hash_uniqueness(self):
        """Test that same password produces different hashes (due to salt)."""
        password = "same_password"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # Hashes should be different due to salt
        assert hash1 != hash2
        
        # Both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True
    
    def test_jwt_token_creation_and_verification(self):
        """Test JWT token creation and verification."""
        user_id = 12345
        token = create_access_token(data={"sub": str(user_id)})
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are typically long
        
        # Verify the token
        payload = verify_token(token, token_type="access")
        assert payload is not None
        assert payload.get("sub") == str(user_id)
    
    def test_invalid_jwt_token_verification(self):
        """Test that invalid tokens return None."""
        invalid_tokens = [
            "invalid.token.here",
            "not.a.token",
            "",
            None,
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid",
        ]
        
        for token in invalid_tokens:
            payload = verify_token(token, token_type="access")
            assert payload is None


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_email_validation(self):
        """Test email validation function."""
        # Valid email addresses
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk", 
            "user+tag@example.net",
            "firstname.lastname@company.org",
            "user123@test-domain.com"
        ]
        
        for email in valid_emails:
            assert validate_email(email) is True, f"Expected {email} to be valid"
        
        # Invalid email addresses
        invalid_emails = [
            "invalid-email",
            "@domain.com",
            "user@",
            "user@domain",
            "",
            None,
            "user space@domain.com",
            "user@domain.",
            ".user@domain.com"
        ]
        
        for email in invalid_emails:
            assert validate_email(email) is False, f"Expected {email} to be invalid"
    
    def test_unique_code_generation(self):
        """Test unique code generation."""
        name = "Test Project"
        user_id = 42
        
        code = generate_unique_code(name, user_id)
        
        # Code should be a string and not empty
        assert isinstance(code, str)
        assert len(code) > 0
        
        # Should contain name prefix (first 3 chars)
        assert code.startswith("TES")
        
        # Should contain user ID (last 2 digits)
        assert "42" in code
        
        # Should have the format NAME-USER-RANDOM
        parts = code.split("-")
        assert len(parts) == 3
        assert parts[0] == "TES"  # Name part
        assert parts[1] == "42"   # User ID part
        assert len(parts[2]) == 4 # Random part should be 4 chars
    
    def test_unique_code_different_for_same_input(self):
        """Test that same inputs produce different codes due to randomness."""
        name = "Same Name"
        user_id = 123
        
        code1 = generate_unique_code(name, user_id)
        code2 = generate_unique_code(name, user_id)
        
        # Codes should be different due to random component
        assert code1 != code2
        
        # But both should have same prefix and user parts
        assert code1.split("-")[0] == code2.split("-")[0]  # Same name part
        assert code1.split("-")[1] == code2.split("-")[1]  # Same user part
        assert code1.split("-")[2] != code2.split("-")[2]  # Different random part
    
    def test_unique_code_edge_cases(self):
        """Test unique code generation with edge cases."""
        # Empty name
        code = generate_unique_code("", 1)
        assert code.startswith("GEN-")  # Should use default prefix
        
        # Very long name
        long_name = "This is a very long project name that exceeds normal limits"
        code = generate_unique_code(long_name, 999)
        assert code.startswith("THI-")  # Should take first 3 chars
        
        # Name with spaces and special characters
        code = generate_unique_code("My Project! @#$", 5)
        assert code.startswith("MYP-")  # Should handle spaces/special chars


class TestStatusCodes:
    """Test HTTP status code constants and validations."""
    
    def test_success_status_codes(self):
        """Test that success status codes are properly defined."""
        from fastapi import status
        
        # Common success codes
        assert status.HTTP_200_OK == 200
        assert status.HTTP_201_CREATED == 201
        assert status.HTTP_204_NO_CONTENT == 204
    
    def test_error_status_codes(self):
        """Test that error status codes are properly defined."""
        from fastapi import status
        
        # Common error codes
        assert status.HTTP_400_BAD_REQUEST == 400
        assert status.HTTP_401_UNAUTHORIZED == 401
        assert status.HTTP_403_FORBIDDEN == 403
        assert status.HTTP_404_NOT_FOUND == 404
        assert status.HTTP_422_UNPROCESSABLE_ENTITY == 422
        assert status.HTTP_500_INTERNAL_SERVER_ERROR == 500


if __name__ == "__main__":
    pytest.main([__file__])