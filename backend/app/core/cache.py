"""Cache of slow reads (Redis, or memory when Redis is unreachable).

Only the vector store routes use it: their lists ask OpenAI about every store.
"""

import json
import logging
import threading
import time
from collections.abc import Callable
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
            logger.warning("Redis not available, using in-memory cache fallback: %s", e)
            self.redis_client = None
            self.redis_available = False
            self.memory_cache = InMemoryCache()
            logger.info("In-memory cache enabled")

    def get(self, key: str) -> Any | None:
        """Get value from cache."""
        if self.redis_available:
            try:
                cached_data = self.redis_client.get(key)
                if cached_data:
                    return json.loads(cached_data)
                return None
            except (redis.RedisError, json.JSONDecodeError) as e:
                logger.error("Cache get error: %s", e)
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
                logger.error("Cache set error: %s", e)
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
                logger.error("Cache delete error: %s", e)
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
                logger.error("Cache delete pattern error: %s", e)
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
                logger.error("Cache flush error: %s", e)
                return False
        elif self.memory_cache:
            return self.memory_cache.flush_all()
        return False


# Global cache instance
cache_service = CacheService()


def cached(key: str, ttl: int, compute: Callable[[], Any]) -> Any:
    """The value stored under `key`, or else `compute()`, stored for `ttl` seconds.

    The value must be plain data (dicts, lists, strings, numbers): Redis keeps
    it as JSON, dates turned into strings.
    """
    hit = cache_service.get(key)
    if hit is not None:
        return hit
    value = compute()
    cache_service.set(key, value, ttl)
    return value


class CacheInvalidator:
    """Only the vector store routes are cached (the list and each store's files,
    which both call OpenAI)."""

    @staticmethod
    def invalidate_vector_store_cache() -> int:
        """Clear every vector store entry (the lists and the files). The list's
        key does not carry store ids, so clearing one store's entries would
        leave the lists stale."""
        return cache_service.delete_pattern("vector_store*")
