from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from starlette.middleware.base import BaseHTTPMiddleware

from anc_gateway.api.models import ErrorResponse, error_payload, flatten_validation_errors
from anc_gateway.api.request_context import REQUEST_ID_HEADER, get_request_id
from anc_gateway.api.routes import router
from anc_gateway.core.source_map import SourceMapAttributionError


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response


def make_error_response(
    *,
    request: Request,
    status_code: int,
    code: str,
    message: str,
) -> JSONResponse:
    request_id = get_request_id(request)
    response = JSONResponse(
        status_code=status_code,
        content=error_payload(code, message, request_id),
    )
    response.headers[REQUEST_ID_HEADER] = request_id
    return response

app = FastAPI(
    title="ANC Render Gateway",
    version="0.6.0a-console",
    description="Minimal FastAPI service wrapper for the ANC parser kernel.",
    responses={
        400: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
app.add_middleware(RequestIDMiddleware)
app.include_router(router)

WEB_STATIC_DIR = Path(__file__).resolve().parents[1] / "web" / "static"
app.mount("/console/static", StaticFiles(directory=WEB_STATIC_DIR), name="console-static")


@app.get("/console", include_in_schema=False)
def console() -> FileResponse:
    return FileResponse(WEB_STATIC_DIR / "index.html")


@app.exception_handler(SourceMapAttributionError)
async def source_map_error_handler(
    request: Request,
    exc: SourceMapAttributionError,
) -> JSONResponse:
    return make_error_response(
        request=request,
        status_code=400,
        code="SOURCE_MAP_ATTRIBUTION_ERROR",
        message=str(exc),
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return make_error_response(
        request=request,
        status_code=400,
        code="VALUE_ERROR",
        message=str(exc),
    )


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return make_error_response(
        request=request,
        status_code=422,
        code="VALIDATION_ERROR",
        message=flatten_validation_errors(exc.errors()),
    )


@app.exception_handler(ValidationError)
async def pydantic_validation_error_handler(
    request: Request,
    exc: ValidationError,
) -> JSONResponse:
    return make_error_response(
        request=request,
        status_code=422,
        code="VALIDATION_ERROR",
        message=flatten_validation_errors(exc.errors()),
    )


@app.exception_handler(Exception)
async def unknown_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return make_error_response(
        request=request,
        status_code=500,
        code="INTERNAL_SERVER_ERROR",
        message="Internal server error",
    )
