"""Weather service module."""

import logging
import re

import httpx
from fastapi import Request

from constants import HTTPResponseCode
from exceptions import WeatherServiceError
from services.cache import CacheService, cache
from validation.weather import WeatherRequest


class WeatherService(CacheService):

    def __init__(self, weather_request: WeatherRequest, request: Request):
        self._log = logging.getLogger(self.__class__.__name__)
        self._city = weather_request.city
        self._response_pattern = re.compile(f"^{self._city}:(.+),(.+)$")
        self._query_url = f"https://wttr.in/{self._city}?format=%l:%C,%t"
        super().__init__(weather_request, request)

    @cache("city")
    async def get_weather(self) -> dict:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self._query_url)
            except httpx.RequestError as err:
                self._log.error(
                    "Fail to get a weather response for city %s: %s", self._city, err
                )
                raise WeatherServiceError(
                    message=f"Fail to get a response for {self._city}",
                    status_code=HTTPResponseCode.BAD_GATEWAY.value,
                )
            if response.status_code != HTTPResponseCode.STATUS_OK.value:
                self._log.warning(
                    "Fail to get a weather response for city %s: %s %s",
                    self._city,
                    response.status_code,
                    response.text,
                )
                raise WeatherServiceError(
                    message=f"Fail to get a response for {self._city}",
                    status_code=HTTPResponseCode.BAD_GATEWAY.value,
                )
            parsed_response = self._parse_weather_response(response.text)
            return parsed_response

    def _parse_weather_response(self, response: str) -> dict:
        match_data = re.findall(self._response_pattern, response)
        if not match_data:
            raise WeatherServiceError(
                message=f"Fail to parse weather response for {self._city}",
                status_code=HTTPResponseCode.INTERNAL_SERVER_ERROR.value,
            )
        condition, temperature = match_data[0]
        parsed_response = {
            "city": self._city,
            "weather condition": condition,
            "actual temperature": temperature,
        }
        return parsed_response
