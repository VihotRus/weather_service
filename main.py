"""API main module."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend

from middlware.error_handler import ErrorHandlerMiddleware
from routes.weather import weather_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    FastAPICache.init(InMemoryBackend())
    yield


app = FastAPI(lifespan=lifespan)


app.include_router(weather_router)

app.add_middleware(ErrorHandlerMiddleware)


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
