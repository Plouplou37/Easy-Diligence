"""Response cache (core/cache.py), on its in-memory fallback.

REDIS_URL points at a closed port in the test settings, so the service always
falls back to memory and a test can never write into a real Redis.
"""

import time
from types import SimpleNamespace

from app.core.cache import CacheInvalidator, CacheService, cache_response


def test_set_get_delete():
    cache = CacheService()
    assert cache.redis_available is False
    assert cache.set("test_key", {"data": "value"}, ttl=60) is True
    assert cache.get("test_key") == {"data": "value"}
    assert cache.get("missing") is None
    assert cache.delete("test_key") is True
    assert cache.get("test_key") is None


def test_key_depends_on_its_parameters():
    cache = CacheService()
    first = cache._generate_cache_key("test", user_id=123, session_id=456)
    assert first == cache._generate_cache_key("test", user_id=123, session_id=456)
    assert first != cache._generate_cache_key("test", user_id=123, session_id=789)
    assert first.startswith("test:")


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


def test_invalidators_do_not_fail():
    assert CacheInvalidator.invalidate_session_cache() >= 0
    assert CacheInvalidator.invalidate_company_cache() >= 0
    assert CacheInvalidator.invalidate_dd_types_cache() >= 0


def test_unserialisable_value_is_refused_quietly():
    assert isinstance(CacheService().set("bad", object()), bool)


# --- The decorator, as the routes use it: keyword arguments only (FastAPI calls
# endpoints that way). The key holds the user and the key_params, nothing else.


async def test_decorator_caches_per_user():
    calls = []

    @cache_response(prefix="per_user", ttl=60)
    async def endpoint(current_user=None):
        calls.append(current_user.id)
        return {"user": current_user.id, "call": len(calls)}

    alice, bob = SimpleNamespace(id=1), SimpleNamespace(id=2)
    assert (await endpoint(current_user=alice))["call"] == 1
    assert (await endpoint(current_user=alice))["call"] == 1  # served from cache
    assert (await endpoint(current_user=bob))["call"] == 2  # another user, another entry
    assert calls == [1, 2]


async def test_decorator_keys_on_the_listed_parameters_only():
    calls = []

    @cache_response(prefix="per_store", ttl=60, key_params=["vector_store_id"])
    async def endpoint(vector_store_id: str, detail: str = "", current_user=None):
        calls.append(vector_store_id)
        return {"store": vector_store_id, "detail": detail}

    user = SimpleNamespace(id=1)
    await endpoint(vector_store_id="vs_1", detail="first", current_user=user)
    # Same store, other unlisted parameter: still the cached answer.
    cached = await endpoint(vector_store_id="vs_1", detail="second", current_user=user)
    assert cached["detail"] == "first"
    await endpoint(vector_store_id="vs_2", detail="third", current_user=user)
    assert calls == ["vs_1", "vs_2"]
