"""
Redis caching service for API response optimization with in-memory fallback
"""

import hashlib
import json
import logging
import threading
import time
from functools import wraps
from typing import Any

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)


class InMemoryCache:
    """Simple in-memory cache with TTL support as fallback when Redis unavailable."""

    def __init__(self):
        self._cache: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> Any | None:
        """Get value from cache if not expired."""
        with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]
            if time.time() > entry["expires_at"]:
                del self._cache[key]
                return None

            return entry["value"]

    def set(self, key: str, value: Any, ttl: int) -> bool:
        """Set value in cache with TTL."""
        with self._lock:
            self._cache[key] = {"value": value, "expires_at": time.time() + ttl}
            return True

    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern (wildcard support)."""
        import fnmatch

        with self._lock:
            keys_to_delete = [k for k in self._cache if fnmatch.fnmatch(k, pattern)]
            logger.debug("Cache: %d keys match %r", len(keys_to_delete), pattern)
            for key in keys_to_delete:
                del self._cache[key]
            return len(keys_to_delete)

    def flush_all(self) -> bool:
        """Clear all cache."""
        with self._lock:
            self._cache.clear()
            return True


class CacheService:
    """Caching service with Redis primary and in-memory fallback."""

    def __init__(self):
        self.default_ttl = 2 * 3600  # 2 heures default

        # Try to connect to Redis
        try:
            self.redis_client = redis.from_url(settings.redis_url)
            self.redis_client.ping()
            self.redis_available = True
            self.memory_cache = None
            logger.info("Redis cache enabled")
        except (redis.RedisError, ConnectionError, AttributeError) as e:
            logger.warning(f"Redis not available, using in-memory cache fallback: {e}")
            self.redis_client = None
            self.redis_available = False
            self.memory_cache = InMemoryCache()
            logger.info("In-memory cache enabled")

    def _generate_cache_key(self, prefix: str, **kwargs) -> str:
        """Generate cache key from prefix and parameters."""
        # Extract vector_store_id if present for better cache key readability and pattern matching
        vector_store_id = kwargs.get("vector_store_id", None)

        # Create a copy without vector_store_id for hashing
        remaining_params = {k: v for k, v in kwargs.items() if k != "vector_store_id"}
        params_str = json.dumps(remaining_params, sort_keys=True)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]

        # Include vector_store_id directly in key if present
        if vector_store_id:
            return f"{prefix}:{vector_store_id}:{params_hash}"
        return f"{prefix}:{params_hash}"

    def get(self, key: str) -> Any | None:
        """Get value from cache."""
        if self.redis_available:
            try:
                cached_data = self.redis_client.get(key)
                if cached_data:
                    return json.loads(cached_data)
                return None
            except (redis.RedisError, json.JSONDecodeError) as e:
                logger.error(f"Cache get error: {e}")
                return None
        elif self.memory_cache:
            return self.memory_cache.get(key)
        return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Set value in cache with TTL."""
        ttl = ttl or self.default_ttl

        if self.redis_available:
            try:
                serialized_value = json.dumps(value, default=str)
                return self.redis_client.setex(key, ttl, serialized_value)
            except (redis.RedisError, json.JSONDecodeError, ValueError) as e:
                logger.error(f"Cache set error: {e}")
                return False
        elif self.memory_cache:
            return self.memory_cache.set(key, value, ttl)
        return False

    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if self.redis_available:
            try:
                return bool(self.redis_client.delete(key))
            except redis.RedisError as e:
                logger.error(f"Cache delete error: {e}")
                return False
        elif self.memory_cache:
            return self.memory_cache.delete(key)
        return False

    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        if self.redis_available:
            try:
                keys = self.redis_client.keys(pattern)
                if keys:
                    return self.redis_client.delete(*keys)
                return 0
            except redis.RedisError as e:
                logger.error(f"Cache delete pattern error: {e}")
                return 0
        elif self.memory_cache:
            return self.memory_cache.delete_pattern(pattern)
        return 0

    def flush_all(self) -> bool:
        """Clear all cache (use with caution)."""
        if self.redis_available:
            try:
                return self.redis_client.flushdb()
            except redis.RedisError as e:
                logger.error(f"Cache flush error: {e}")
                return False
        elif self.memory_cache:
            return self.memory_cache.flush_all()
        return False


# Global cache instance
cache_service = CacheService()


def cache_response(
    prefix: str, ttl: int = 300, key_params: list | None = None, user_specific: bool = True
):
    """
    Decorator for caching API responses.

    Args:
        prefix: Cache key prefix (e.g., 'sessions', 'companies')
        ttl: Time to live in seconds (default: 5 minutes)
        key_params: List of parameter names to include in cache key
        user_specific: Whether to include user ID in cache key
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract current user if user_specific caching
            cache_key_params = {}

            if user_specific and "current_user" in kwargs:
                cache_key_params["user_id"] = kwargs["current_user"].id

            # Include specified parameters in cache key
            if key_params:
                for param in key_params:
                    if param in kwargs:
                        cache_key_params[param] = kwargs[param]

            # Generate cache key
            cache_key = cache_service._generate_cache_key(prefix, **cache_key_params)

            # Try to get from cache
            cached_result = cache_service.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache HIT for key: {cache_key}")
                return cached_result
            else:
                logger.debug(f"Cache MISS for key: {cache_key}")

            # Execute function and cache result
            result = await func(*args, **kwargs)

            # Pydantic models are stored as plain data.
            if hasattr(result, "model_dump"):
                cache_data = result.model_dump()
            elif isinstance(result, list):
                cache_data = [
                    item.model_dump() if hasattr(item, "model_dump") else item for item in result
                ]
            else:
                cache_data = result

            # Cache the result
            cache_service.set(cache_key, cache_data, ttl)
            logger.debug(f"Cache SET for key: {cache_key} with TTL: {ttl}s")

            return result

        return wrapper

    return decorator


class CacheInvalidator:
    """Only the vector store routes are cached (the list and each store's files,
    which both call OpenAI)."""

    @staticmethod
    def invalidate_vector_store_cache() -> int:
        """Clear every vector store entry. The list's key does not carry store
        ids, so clearing a single store's entries would leave it stale."""
        return cache_service.delete_pattern("vector_store*")
