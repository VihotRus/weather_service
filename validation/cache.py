"""Request validation class for the response that can be cached."""

from typing import Optional

from pydantic import BaseModel, PositiveInt


class CacheRequest(BaseModel):
    cache_ttl: Optional[PositiveInt] = None
    cache_bypass: Optional[bool] = None
