"""Response cache (core/cache.py), on its in-memory fallback.

REDIS_URL points at a closed port in the test settings, so the service always
falls back to memory and a test can never write into a real Redis.
"""

import time

from app.core.cache import CacheInvalidator, CacheService, cache_service, cached


def test_set_get_delete():
    cache = CacheService()
    assert cache.redis_available is False
    assert cache.set("test_key", {"data": "value"}, ttl=60) is True
    assert cache.get("test_key") == {"data": "value"}
    assert cache.get("missing") is None
    assert cache.delete("test_key") is True
    assert cache.get("test_key") is None


def test_entries_expire():
    cache = CacheService()
    cache.set("expiring", {"data": 1}, ttl=1)
    assert cache.get("expiring") == {"data": 1}
    time.sleep(1.1)
    assert cache.get("expiring") is None


def test_delete_by_pattern():
    cache = CacheService()
    cache.set("user:123:sessions", {"data": 1})
    cache.set("user:123:profile", {"data": 2})
    cache.set("user:456:sessions", {"data": 3})
    assert cache.delete_pattern("user:123:*") == 2
    assert cache.get("user:123:sessions") is None
    assert cache.get("user:456:sessions") == {"data": 3}


def test_vector_store_invalidation_clears_every_store_entry():
    cache_service.set("vector_stores:abc123", ["the list"])
    cache_service.set("vector_store_files:vs_1:def456", ["a file"])
    cache_service.set("other:1", "kept")
    assert CacheInvalidator.invalidate_vector_store_cache() == 2
    assert cache_service.get("vector_stores:abc123") is None
    assert cache_service.get("other:1") == "kept"


def test_unserialisable_value_is_refused_quietly():
    assert isinstance(CacheService().set("bad", object()), bool)


# --- cached(): what the vector store service uses.


def test_cached_computes_once_then_serves_the_stored_value():
    calls = []

    def compute():
        calls.append(1)
        return [{"id": "vs_1"}]

    assert cached("vector_stores:1", 60, compute) == [{"id": "vs_1"}]
    assert cached("vector_stores:1", 60, compute) == [{"id": "vs_1"}]
    assert len(calls) == 1
    assert cached("vector_stores:2", 60, compute) == [{"id": "vs_1"}]  # another key
    assert len(calls) == 2


def test_cached_does_not_store_what_keep_refuses():
    answers = iter([["incomplete"], ["complete"]])

    def compute():
        return next(answers)

    def keep(value):
        return value == ["complete"]

    assert cached("vector_stores:1", 60, compute, keep) == ["incomplete"]
    assert cached("vector_stores:1", 60, compute, keep) == ["complete"]
    assert cached("vector_stores:1", 60, compute, keep) == ["complete"]  # now stored
