"""Weather request validation models."""

from pydantic import field_validator

from validation.cache import CacheRequest


class WeatherRequest(CacheRequest):
    city: str

    @field_validator("city")
    def normalize_city(cls, city: str):
        return city.lower()
