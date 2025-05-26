import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routes.weather import weather_router
from services.cache import FastAPICache
from services.weather import WeatherService, WeatherServiceError

app = FastAPI()
app.include_router(weather_router)


class FakeBackend:
    def __init__(self):
        self.store = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, expire):
        self.store[key] = value
        return True


@pytest.fixture(autouse=True)
def patch_cache_backend(monkeypatch):
    backend = FakeBackend()
    monkeypatch.setattr(FastAPICache, "get_backend", lambda self: backend)
    return backend


def test_get_weather_validation_error():
    client = TestClient(app)
    response = client.post("/weather/", json={})
    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload", [{"city": 123}, {"cache_ttl": 5}]  # invalid type  # missing city
)
def test_get_weather_bad_input(payload):
    client = TestClient(app)
    response = client.post("/weather/", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
def test_get_weather_service_success(monkeypatch):
    sample = {
        "city": "test",
        "weather condition": "Clear",
        "actual temperature": "+20C",
    }

    async def fake_get(self):
        return 7, True, sample

    monkeypatch.setattr(WeatherService, "get_weather", fake_get)

    client = TestClient(app)
    response = client.post("/weather/", json={"city": "TestCity"})
    assert response.status_code == 200
    assert response.json() == sample
    assert response.headers.get("X-Cache-Status") == "HIT"
    assert response.headers.get("X-Cache-TTL") == "7"


@pytest.mark.asyncio
def test_get_weather_service_error(monkeypatch):
    async def fake_get(self):
        raise WeatherServiceError(message="fail", status_code=502)

    monkeypatch.setattr(WeatherService, "get_weather", fake_get)

    client = TestClient(app, raise_server_exceptions=False)
    response = client.post("/weather/", json={"city": "ErrCity"})
    assert response.status_code == 500
