"""Constants module."""

from enum import Enum


class HTTPResponseCode(Enum):
    STATUS_OK = 200
    BAD_REQUEST = 400
    INTERNAL_SERVER_ERROR = 500
    BAD_GATEWAY = 502


DEFAULT_CACHE_TTL = 60 * 60  # 1 hour
MAX_CACHE_TTL = 60 * 60 * 24 * 30  # 1 month
