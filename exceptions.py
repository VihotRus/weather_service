"""Custom exceptions module."""


class ServiceError(Exception):
    """Raise when there is an error in service."""

    def __init__(self, message: str, status_code: int):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class WeatherServiceError(ServiceError):
    """Raise when there is an error in weather service."""


class CacheServiceError(ServiceError):
    """Raise when there is an error in cache service."""
