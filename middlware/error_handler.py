"""Error handler middleware module."""

import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from constants import HTTPResponseCode
from exceptions import ServiceError


class ErrorHandlerMiddleware(BaseHTTPMiddleware):

    def __init__(self, *args, **kwargs):
        self._log = logging.getLogger(__name__)
        super().__init__(*args, **kwargs)

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
        except ServiceError as err:
            return JSONResponse(
                status_code=err.status_code, content={"error": err.message}
            )
        except Exception as err:
            self._log.error("Unexpected error during request processing: %s", err)
            response = JSONResponse(
                status_code=HTTPResponseCode.INTERNAL_SERVER_ERROR.value,
                content={"error": "Internal Server Error"},
            )
        return response
