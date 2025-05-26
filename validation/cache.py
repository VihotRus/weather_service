"""Request validation class for the response that can be cached."""

from typing import Optional

from pydantic import BaseModel, PositiveInt


class CacheRequest(BaseModel):
    ttl: Optional[PositiveInt] = None
    bypass: Optional[bool] = None
