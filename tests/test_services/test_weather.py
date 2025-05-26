import json
import re

import httpx
import pytest

from services.cache import FastAPICache
from services.weather import (HTTPResponseCode, WeatherService,
                              WeatherServiceError)


class DummyRequest:
    def __init__(self, headers=None):
        self.headers = headers or {}


class DummyWeatherRequest:
    def __init__(self, city, cache_ttl=None, cache_bypass=False):
        self.city = city
        self.cache_ttl = cache_ttl
        self.cache_bypass = cache_bypass


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
    backend = FakeBackend()
    monkeypatch.setattr(FastAPICache, "get_backend", lambda self: backend)
    return backend


def test_init_fields_and_pattern():
    req = DummyWeatherRequest(city="TestCity", cache_ttl=3, cache_bypass=True)
    request = DummyRequest(headers={})
    service = WeatherService(req, request)
    assert service._city == "TestCity"
    assert service._query_url == "https://wttr.in/TestCity?format=%l:%C,%t"
    assert isinstance(service._response_pattern, re.Pattern)
    # Inherited cache fields
    assert isinstance(service.cache_ttl, int)
    assert isinstance(service.cache_bypass, bool)
    assert hasattr(service, "cache_backend")


def test_parse_weather_response_success():
    req = DummyWeatherRequest(city="X", cache_ttl=None, cache_bypass=False)
    request = DummyRequest()
    service = WeatherService(req, request)
    text = "X:Clear,+25C"
    result = service._parse_weather_response(text)
    assert result == {
        "city": "X",
        "weather condition": "Clear",
        "actual temperature": "+25C",
    }


def test_parse_weather_response_failure():
    req = DummyWeatherRequest(city="Y", cache_ttl=None, cache_bypass=False)
    request = DummyRequest()
    service = WeatherService(req, request)
    with pytest.raises(WeatherServiceError) as excinfo:
        service._parse_weather_response("InvalidResponse")
    assert excinfo.value.status_code == HTTPResponseCode.INTERNAL_SERVER_ERROR.value


class ErrorClient:
    async def get(self, url):
        raise httpx.RequestError("fail", request=None)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class Non200Client:
    def __init__(self):
        self.status_code = 500
        self.text = "error"

    async def get(self, url):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class SuccessClient:
    def __init__(self, response_text):
        self.status_code = HTTPResponseCode.STATUS_OK.value
        self.text = response_text

    async def get(self, url):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_get_weather_request_error(monkeypatch, patch_backend):
    monkeypatch.setattr(httpx, "AsyncClient", lambda: ErrorClient())
    req = DummyWeatherRequest(city="Z", cache_ttl=None, cache_bypass=False)
    request = DummyRequest()
    service = WeatherService(req, request)
    with pytest.raises(WeatherServiceError) as excinfo:
        await service.get_weather()
    assert excinfo.value.status_code == HTTPResponseCode.BAD_GATEWAY.value


@pytest.mark.asyncio
async def test_get_weather_non_200(monkeypatch, patch_backend):
    monkeypatch.setattr(httpx, "AsyncClient", lambda: Non200Client())
    req = DummyWeatherRequest(city="A", cache_ttl=None, cache_bypass=False)
    request = DummyRequest()
    service = WeatherService(req, request)
    with pytest.raises(WeatherServiceError) as excinfo:
        await service.get_weather()
    assert excinfo.value.status_code == HTTPResponseCode.BAD_GATEWAY.value


@pytest.mark.asyncio
async def test_get_weather_success_and_parse(monkeypatch, patch_backend):
    text = "City1:Sunny,+30C"
    monkeypatch.setattr(httpx, "AsyncClient", lambda: SuccessClient(text))
    req = DummyWeatherRequest(city="City1", cache_ttl=None, cache_bypass=False)
    request = DummyRequest()
    service = WeatherService(req, request)
    result = await service.get_weather()
    assert result == (
        0,
        False,
        {"city": "City1", "weather condition": "Sunny", "actual temperature": "+30C"},
    )


@pytest.mark.asyncio
async def test_get_weather_cache_hit(monkeypatch, patch_backend):
    data = {"city": "City2", "weather condition": "Rain", "actual temperature": "+10C"}
    patch_backend.store["City2"] = json.dumps(data).encode()
    req = DummyWeatherRequest(city="City2", cache_ttl=None, cache_bypass=False)
    request = DummyRequest()
    service = WeatherService(req, request)
    result = await service.get_weather()
    assert result == (0, True, data)
    assert patch_backend.get_calls == ["City2"]
    assert patch_backend.set_calls == []


@pytest.mark.asyncio
async def test_get_weather_cache_miss_then_set(monkeypatch, patch_backend):
    text = "City3:Cloudy,+20C"
    monkeypatch.setattr(httpx, "AsyncClient", lambda: SuccessClient(text))
    req = DummyWeatherRequest(city="City3", cache_ttl=12, cache_bypass=False)
    request = DummyRequest()
    service = WeatherService(req, request)
    result = await service.get_weather()
    assert result == (
        0,
        False,
        {"city": "City3", "weather condition": "Cloudy", "actual temperature": "+20C"},
    )
    assert patch_backend.get_calls == ["City3"]
    assert len(patch_backend.set_calls) == 1
    key, raw, expire = patch_backend.set_calls[0]
    assert key == "City3"
    assert json.loads(raw.decode()) == result[-1]
    assert expire == 12
