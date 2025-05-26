import pytest
from pydantic import PositiveInt, ValidationError

from validation import cache, weather


def test_cache_request_defaults():
    cr = cache.CacheRequest()
    assert cr.cache_ttl is None
    assert cr.cache_bypass is None


@pytest.mark.parametrize("value", [1, 10, 100])
def test_cache_request_ttl_positive(value):
    cr = cache.CacheRequest(cache_ttl=value)
    assert cr.cache_ttl == value


@pytest.mark.parametrize("value", [0, -1])
def test_cache_request_invalid_ttl(value):
    with pytest.raises(ValidationError):
        cache.CacheRequest(cache_ttl=value)


@pytest.mark.parametrize("value", [True, False])
def test_cache_request_bypass_bool(value):
    cr = cache.CacheRequest(cache_bypass=value)
    assert isinstance(cr.cache_bypass, bool)
    assert cr.cache_bypass is value


def test_weather_request_normalizes_city_lowercase():
    wr = weather.WeatherRequest(city="TeStCiTy")
    assert wr.city == "testcity"
    assert wr.cache_ttl is None
    assert wr.cache_bypass is None


@pytest.mark.parametrize(
    "city,ttl,bypass",
    [("London", 5, True), ("NEWYORK", 2, False)],
)
def test_weather_request_with_cache_params(city, ttl, bypass):
    wr = weather.WeatherRequest(city=city, cache_ttl=ttl, cache_bypass=bypass)
    assert wr.city == city.lower()
    assert wr.cache_ttl == ttl
    assert wr.cache_bypass is bypass


@pytest.mark.parametrize("bad_city", [123, None])
def test_weather_request_missing_or_bad_city(bad_city):
    with pytest.raises(ValidationError):
        weather.WeatherRequest(city=bad_city)


def test_weather_request_missing_city_field():
    with pytest.raises(ValidationError):
        weather.WeatherRequest(cache_ttl=1, cache_bypass=False)
