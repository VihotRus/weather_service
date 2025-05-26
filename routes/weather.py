"""Weather route module."""

from fastapi import APIRouter, Request

from services.weather import WeatherService
from validation.weather import WeatherRequest

weather_router = APIRouter(prefix="/weather", tags=["weather"])


@weather_router.post("/")
async def get_weather(weather_request: WeatherRequest, request: Request):
    weather_service = WeatherService(weather_request, request)
    response = await weather_service.get_weather()
    return response
