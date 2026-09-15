from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes_deep_research import router as deep_research_router
from app.api.routes_sec import router as sec_router
from app.api.routes_stocks import router as stocks_router
from app.core.config import get_settings
from app.core.errors import (
    AppError,
    ErrorCode,
    ErrorDetail,
    ErrorResponse,
)
from app.core.logging import configure_logging, get_logger
from app.core.request_id import RequestIdMiddleware, get_request_id
from app.schemas.common import ApiResponse
from app.schemas.errors import HealthErrorResponse

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info("service_starting", extra={"service": settings.app_name})
    yield
    logger.info("service_stopping", extra={"service": settings.app_name})


def create_app() -> FastAPI:
    application = FastAPI(
        title="AI Equity Research Agent API",
        version=settings.app_version,
        description="Backend foundation for the AI Equity Research Agent.",
        lifespan=lifespan,
    )
    application.add_middleware(RequestIdMiddleware)
    application.include_router(stocks_router)
    application.include_router(sec_router)
    application.include_router(deep_research_router)

    @application.get(
        "/health",
        response_model=ApiResponse[HealthErrorResponse],
        tags=["system"],
    )
    async def health(request: Request) -> ApiResponse[HealthErrorResponse]:
        del request
        return ApiResponse(
            request_id=get_request_id(),
            data=HealthErrorResponse(
                status="ok",
                service=settings.app_name,
                version=settings.app_version,
                environment=settings.app_env,
                data_mode=settings.data_mode,
            ),
        )

    @application.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        response = ErrorResponse(
            request_id=get_request_id(),
            errors=[
                ErrorDetail(
                    code=exc.code,
                    message=exc.message,
                    retryable=exc.retryable,
                    details=exc.details,
                )
            ],
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=response.model_dump(mode="json"),
        )

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        response = ErrorResponse(
            request_id=get_request_id(),
            errors=[
                ErrorDetail(
                    code=ErrorCode.VALIDATION_ERROR,
                    message="Request validation failed.",
                    details={"validation_errors": exc.errors()},
                )
            ],
        )
        return JSONResponse(status_code=422, content=response.model_dump(mode="json"))

    @application.exception_handler(StarletteHTTPException)
    async def http_error_handler(
        _: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        response = ErrorResponse(
            request_id=get_request_id(),
            errors=[
                ErrorDetail(
                    code=ErrorCode.HTTP_ERROR,
                    message=str(exc.detail),
                )
            ],
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=response.model_dump(mode="json"),
        )

    @application.exception_handler(Exception)
    async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unhandled_exception",
            extra={"exception_type": type(exc).__name__},
        )
        response = ErrorResponse(
            request_id=get_request_id(),
            errors=[
                ErrorDetail(
                    code=ErrorCode.INTERNAL_ERROR,
                    message="An unexpected internal error occurred.",
                )
            ],
        )
        return JSONResponse(status_code=500, content=response.model_dump(mode="json"))

    return application


app = create_app()
