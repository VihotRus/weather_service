import json
import logging

import pytest

from services.cache import (DEFAULT_CACHE_TTL, MAX_CACHE_TTL, CacheService,
                            CacheServiceError, FastAPICache, HTTPResponseCode,
                            cache)


# Dummy classes to simulate request and cache_request
class DummyRequest:
    def __init__(self, headers=None):
        self.headers = headers or {}


class DummyCacheRequest:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


# Fake in-memory cache backend
class FakeBackend:
    def __init__(self):
        self.store = {}
        self.get_calls = []
        self.set_calls = []

    async def get_with_ttl(self, key):
        self.get_calls.append(key)
        return 0, self.store.get(key)

    async def set(self, key, value, expire):
        self.set_calls.append((key, value, expire))
        self.store[key] = value
        return True


@pytest.fixture(autouse=True)
def patch_backend(monkeypatch):
    """
    Monkeypatch FastAPICache.get_backend to return our FakeBackend.
    """
    backend = FakeBackend()
    monkeypatch.setattr(FastAPICache, "get_backend", lambda self: backend)
    return backend


# Tests for header parsing
@pytest.mark.parametrize(
    "value, expected",
    [
        ("10", 10),
        ("1", 1),
        ("999", 999),
    ],
)
def test_parse_cache_ttl_header_valid(value, expected):
    assert CacheService._parse_cache_ttl_header(value) == expected


@pytest.mark.parametrize("value", ["0", "-1", "abc"])
def test_parse_cache_ttl_header_invalid(value):
    with pytest.raises(CacheServiceError) as excinfo:
        CacheService._parse_cache_ttl_header(value)
    assert excinfo.value.status_code == HTTPResponseCode.BAD_REQUEST.value


@pytest.mark.parametrize(
    "value, expected",
    [
        ("1", True),
        ("true", True),
        ("yes", True),
        ("on", True),
        ("0", False),
        ("false", False),
        ("no", False),
        ("off", False),
    ],
)
def test_parse_cache_bypass_header_valid(value, expected):
    assert CacheService._parse_cache_bypass_header(value) is expected


def test_parse_cache_bypass_header_invalid():
    with pytest.raises(CacheServiceError) as excinfo:
        CacheService._parse_cache_bypass_header("maybe")
    assert excinfo.value.status_code == HTTPResponseCode.BAD_REQUEST.value


# Tests for __init__ logic
def test_init_defaults(monkeypatch, patch_backend):
    cache_request = DummyCacheRequest(cache_ttl=None, cache_bypass=False)
    request = DummyRequest(headers={})
    service = CacheService(cache_request, request)
    assert service.cache_ttl == DEFAULT_CACHE_TTL
    assert service.cache_bypass is False
    assert service.cache_backend is patch_backend


def test_init_header_ttl_and_bypass(monkeypatch, patch_backend):
    headers = {"X-Cache-TTL": "5", "X-Cache-Bypass": "true"}
    cache_request = DummyCacheRequest(cache_ttl=1, cache_bypass=False)
    request = DummyRequest(headers=headers)
    service = CacheService(cache_request, request)
    assert service.cache_ttl == 5
    assert service.cache_bypass is True


def test_init_max_ttl_warning(monkeypatch, caplog, patch_backend):
    headers = {"X-Cache-TTL": str(MAX_CACHE_TTL + 100)}
    cache_request = DummyCacheRequest(cache_ttl=None, cache_bypass=False)
    request = DummyRequest(headers=headers)
    caplog.set_level(logging.WARNING)
    service = CacheService(cache_request, request)
    assert service.cache_ttl == MAX_CACHE_TTL
    assert "exceeds maximum allowed value" in caplog.text


# Helper service class with decorated method
class TestService(CacheService):
    def __init__(self, cache_request, request):
        super().__init__(cache_request, request)

    @cache("key")
    async def get_data(self, value):
        return {"value": value}


@pytest.mark.asyncio
async def test_cache_decorator_bypass(patch_backend):
    cache_request = DummyCacheRequest(key="k1", cache_ttl=10, cache_bypass=True)
    request = DummyRequest(headers={})
    service = TestService(cache_request, request)
    result = await service.get_data(42)
    assert result == (0, False, {"value": 42})
    assert patch_backend.get_calls == []
    assert patch_backend.set_calls == []


@pytest.mark.asyncio
async def test_cache_decorator_missing_key(patch_backend):
    cache_request = DummyCacheRequest(other="x", cache_ttl=5, cache_bypass=False)
    request = DummyRequest(headers={})
    service = TestService(cache_request, request)
    with pytest.raises(CacheServiceError) as excinfo:
        await service.get_data(1)
    assert excinfo.value.status_code == HTTPResponseCode.INTERNAL_SERVER_ERROR.value


@pytest.mark.asyncio
async def test_cache_decorator_hit(patch_backend):
    cache_request = DummyCacheRequest(key="k2", cache_ttl=5, cache_bypass=False)
    request = DummyRequest(headers={})
    backend = patch_backend
    value = {"value": 99}
    backend.store["k2"] = json.dumps(value).encode()
    service = TestService(cache_request, request)
    result = await service.get_data(None)
    assert result == (0, True, value)
    assert backend.get_calls == ["k2"]
    assert backend.set_calls == []


@pytest.mark.asyncio
async def test_cache_decorator_miss_then_set(patch_backend):
    cache_request = DummyCacheRequest(key="k3", cache_ttl=7, cache_bypass=False)
    request = DummyRequest(headers={})
    backend = patch_backend
    service = TestService(cache_request, request)
    result = await service.get_data(123)
    assert result == (0, False, {"value": 123})
    assert backend.get_calls == ["k3"]
    assert len(backend.set_calls) == 1
    key, raw, expire = backend.set_calls[0]
    assert key == "k3"
    assert json.loads(raw.decode()) == {"value": 123}
    assert expire == 7
