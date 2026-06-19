from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .responses import ApiResponse, BusinessError

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BusinessError)
    async def business_error_handler(request: Request, exc: BusinessError) -> JSONResponse:
        response = ApiResponse(
            code=exc.code,
            message=exc.message,
            data=exc.details,
        )
        return JSONResponse(
            status_code=exc.code,
            content=response.model_dump(),
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        response = ApiResponse(
            code=422,
            message=str(exc),
        )
        return JSONResponse(
            status_code=422,
            content=response.model_dump(),
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception")
        response = ApiResponse(
            code=500,
            message="Internal server error",
        )
        return JSONResponse(
            status_code=500,
            content=response.model_dump(),
        )