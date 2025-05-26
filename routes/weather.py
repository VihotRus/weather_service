"""Weather route module."""

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

from constants import HTTPResponseCode
from services.weather import WeatherService
from validation.weather import WeatherRequest

weather_router = APIRouter(prefix="/weather", tags=["weather"])


@weather_router.post("/")
async def get_weather(weather_request: WeatherRequest, request: Request):
    weather_service = WeatherService(weather_request, request)
    cache_ttl, cache_hit, response = await weather_service.get_weather()
    cache_status = "HIT" if cache_hit else "MISS"
    headers = {
        "X-Cache-Status": cache_status,
        "X-Cache-TTL": str(cache_ttl),
    }
    return JSONResponse(
        status_code=HTTPResponseCode.STATUS_OK.value,
        content=response,
        headers=headers,
    )
