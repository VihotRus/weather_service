"""Cached service module."""

import json
import logging
from functools import wraps
from typing import Callable

from fastapi import Request
from fastapi_cache import FastAPICache
from fastapi_cache.types import Backend

from constants import DEFAULT_CACHE_TTL, MAX_CACHE_TTL, HTTPResponseCode
from exceptions import CacheServiceError
from validation.cache import CacheRequest


def cache(key_field: str) -> Callable:
    """Decorator to apply cache logic to methods of CacheService child classes."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(object_: CacheService, *args, **kwargs):
            if object_.cache_bypass:
                response = await func(object_, *args, **kwargs)
            else:
                try:
                    key = getattr(object_.cache_request, key_field)
                except AttributeError:
                    raise CacheServiceError(
                        "Incorrect cache key field setup",
                        HTTPResponseCode.INTERNAL_SERVER_ERROR.value,
                    )
                cached_data = await object_.cache_backend.get(key)
                if cached_data:
                    response = json.loads(cached_data.decode())
                else:
                    response = await func(object_, *args, **kwargs)
                    await object_.cache_backend.set(
                        key, json.dumps(response).encode(), expire=object_.cache_ttl
                    )
            return response

        return wrapper

    return decorator


class CacheService:

    def __init__(self, cache_request: CacheRequest, request: Request):
        self._log = logging.getLogger(self.__class__.__name__)
        self._cache_request = cache_request
        self._request = request
        self._cache_backend = FastAPICache().get_backend()
        header_cache_ttl = request.headers.get("X-Cache-TTL")
        if header_cache_ttl:
            header_cache_ttl = self._parse_cache_ttl_header(header_cache_ttl)
        self._cache_ttl = (
            header_cache_ttl or cache_request.cache_ttl or DEFAULT_CACHE_TTL
        )
        header_cache_bypass = request.headers.get("X-Cache-Bypass")
        if header_cache_bypass:
            header_cache_bypass = self._parse_cache_bypass_header(header_cache_bypass)
        self._cache_bypass = header_cache_bypass or cache_request.cache_bypass
        if self._cache_ttl > MAX_CACHE_TTL:
            self._log.warning(
                "Cache TTL exceeds maximum allowed value, updated to %s", MAX_CACHE_TTL
            )
            self._cache_ttl = MAX_CACHE_TTL

    @property
    def cache_request(self) -> CacheRequest:
        return self._cache_request

    @property
    def cache_ttl(self) -> int:
        return self._cache_ttl

    @property
    def cache_bypass(self) -> bool:
        return self._cache_bypass

    @property
    def cache_backend(self) -> Backend:
        return self._cache_backend

    @staticmethod
    def _parse_cache_ttl_header(value: str):
        try:
            value = int(value)
            if value <= 0:
                raise ValueError
        except ValueError:
            raise CacheServiceError(
                message="X-Cache-TTL value must be a positive integer",
                status_code=HTTPResponseCode.BAD_REQUEST.value,
            )
        return value

    @staticmethod
    def _parse_cache_bypass_header(value: str):
        truthy = ("1", "true", "yes", "on")
        falsy = ("0", "false", "no", "off")
        value = value.lower()
        if value in truthy:
            result = True
        elif value in falsy:
            result = False
        else:
            raise CacheServiceError(
                message=f"X-Cache-Bypass value must be one of the following: {truthy} or {falsy}",
                status_code=HTTPResponseCode.BAD_REQUEST.value,
            )
        return result
