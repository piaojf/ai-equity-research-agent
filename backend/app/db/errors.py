"""Database error translation kept below the service boundary."""

from collections.abc import Awaitable, Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from sqlalchemy.exc import SQLAlchemyError

from app.core.errors import AppError, ErrorCode

P = ParamSpec("P")
T = TypeVar("T")


def database_app_error(operation: str, exc: BaseException) -> AppError:
    """Return a stable public error without leaking driver details."""

    return AppError(
        ErrorCode.DATABASE_ERROR,
        f"Database operation failed: {operation}.",
        status_code=503,
        retryable=isinstance(exc, SQLAlchemyError),
    )


def translate_database_errors(
    operation: str,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Translate SQLAlchemy driver exceptions at repository boundaries."""

    def decorator(
        function: Callable[P, Awaitable[T]],
    ) -> Callable[P, Awaitable[T]]:
        @wraps(function)
        async def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return await function(*args, **kwargs)
            except AppError:
                raise
            except SQLAlchemyError as exc:
                raise database_app_error(operation, exc) from exc

        return wrapped

    return decorator
