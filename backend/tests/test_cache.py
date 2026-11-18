"""
Tests for API response caching functionality
"""

import time

import pytest

from app.core.cache import CacheInvalidator, CacheService, cache_response


class TestCacheService:
    """Test the core caching service."""

    def test_cache_service_basic_operations(self):
        """Test basic cache operations."""
        cache = CacheService()

        # Test set and get
        assert cache.set("test_key", {"data": "test_value"}, ttl=60) is True
        cached_data = cache.get("test_key")
        assert cached_data == {"data": "test_value"}

        # Test non-existent key
        assert cache.get("non_existent_key") is None

        # Test delete
        assert cache.delete("test_key") is True
        assert cache.get("test_key") is None

    def test_cache_key_generation(self):
        """Test cache key generation with parameters."""
        cache = CacheService()

        key1 = cache._generate_cache_key("test", user_id=123, session_id=456)
        key2 = cache._generate_cache_key("test", user_id=123, session_id=456)
        key3 = cache._generate_cache_key("test", user_id=123, session_id=789)

        # Same parameters should generate same key
        assert key1 == key2

        # Different parameters should generate different keys
        assert key1 != key3

        # Keys should contain prefix
        assert key1.startswith("test:")

    def test_cache_ttl_expiration(self):
        """Test that cache entries expire after TTL."""
        cache = CacheService()

        # Set with very short TTL
        cache.set("expire_test", {"data": "expires"}, ttl=1)

        # Should exist immediately
        assert cache.get("expire_test") == {"data": "expires"}

        # Should expire after TTL
        time.sleep(1.1)
        assert cache.get("expire_test") is None

    def test_cache_pattern_deletion(self):
        """Test deletion by pattern."""
        cache = CacheService()

        # Set multiple keys with pattern
        cache.set("user:123:sessions", {"data": "user_sessions"})
        cache.set("user:123:profile", {"data": "user_profile"})
        cache.set("user:456:sessions", {"data": "other_user"})

        # Delete by pattern
        deleted_count = cache.delete_pattern("user:123:*")
        assert deleted_count == 2

        # Check what remains
        assert cache.get("user:123:sessions") is None
        assert cache.get("user:123:profile") is None
        assert cache.get("user:456:sessions") == {"data": "other_user"}


class TestCacheInvalidators:
    """Test cache invalidation helpers."""

    def test_cache_invalidators(self):
        """Test cache invalidation helper methods."""
        cache = CacheService()

        # Set some test data
        cache.set("session_list:abc123", {"sessions": []})
        cache.set("company_list:def456", {"companies": []})
        cache.set("dd_type_list:ghi789", {"dd_types": []})

        # Test invalidation methods don't error
        assert CacheInvalidator.invalidate_session_cache() >= 0
        assert CacheInvalidator.invalidate_company_cache() >= 0
        assert CacheInvalidator.invalidate_dd_types_cache() >= 0


@pytest.mark.asyncio
class TestCacheDecorator:
    """Test the cache response decorator."""

    async def test_cache_decorator_basic(self):
        """Test that cache decorator works correctly."""
        call_count = 0

        @cache_response(prefix="test_func", ttl=60)
        async def test_function(value: str, current_user=None):
            nonlocal call_count
            call_count += 1
            return {"result": f"processed_{value}", "call_count": call_count}

        # Mock user object
        class MockUser:
            def __init__(self, user_id):
                self.id = user_id

        user = MockUser(123)

        # First call should execute function
        result1 = await test_function("test1", current_user=user)
        assert result1["result"] == "processed_test1"
        assert result1["call_count"] == 1
        assert call_count == 1

        # Second call with same parameters should use cache
        result2 = await test_function("test1", current_user=user)
        assert result2["result"] == "processed_test1"
        assert result2["call_count"] == 1  # Should be cached value
        assert call_count == 1  # Function should not have been called again

        # Different parameters should execute function again
        result3 = await test_function("test2", current_user=user)
        assert result3["result"] == "processed_test2"
        assert result3["call_count"] == 2
        assert call_count == 2

    async def test_cache_decorator_with_key_params(self):
        """Test cache decorator with specific key parameters."""
        call_count = 0

        @cache_response(prefix="parameterized", ttl=60, key_params=["important_param"])
        async def parameterized_function(
            important_param: str, ignored_param: str, current_user=None
        ):
            nonlocal call_count
            call_count += 1
            return {"param": important_param, "ignored": ignored_param, "count": call_count}

        class MockUser:
            def __init__(self, user_id):
                self.id = user_id

        user = MockUser(456)

        # First call
        await parameterized_function("key1", "value1", current_user=user)
        assert call_count == 1

        # Same important_param, different ignored_param should use cache
        result2 = await parameterized_function("key1", "different_value", current_user=user)
        assert result2["ignored"] == "value1"  # Should be cached value
        assert call_count == 1  # Function not called again

        # Different important_param should call function
        result3 = await parameterized_function("key2", "value3", current_user=user)
        assert result3["ignored"] == "value3"
        assert call_count == 2


def test_cache_graceful_degradation():
    """Test that cache failures don't break the application."""
    # This test would require mocking Redis failures
    # For now, we test that the service handles basic errors gracefully
    cache = CacheService()

    # Test with invalid data that might cause JSON serialization issues
    class NonSerializable:
        def __repr__(self):
            return "NonSerializable object"

    # Should not raise exception, but return False
    result = cache.set("bad_data", NonSerializable())
    # This might succeed depending on how json handles it, but shouldn't crash
    assert isinstance(result, bool)
