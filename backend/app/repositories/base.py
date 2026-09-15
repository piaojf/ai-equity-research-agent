"""Shared async repository primitives."""

from typing import Any

from sqlalchemy import Executable
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.db.errors import database_app_error


class Repository:
    """A repository receives a session; it never owns a transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def execute(self, statement: Executable, operation: str) -> Any:
        try:
            return await self.session.execute(statement)
        except SQLAlchemyError as exc:
            raise database_app_error(operation, exc) from exc

    async def flush(self, operation: str) -> None:
        try:
            await self.session.flush()
        except SQLAlchemyError as exc:
            raise database_app_error(operation, exc) from exc

    async def scalar_one_or_none(
        self,
        statement: Select[Any],
        operation: str,
    ) -> Any:
        result = await self.execute(statement, operation)
        try:
            return result.scalar_one_or_none()
        except SQLAlchemyError as exc:
            raise database_app_error(operation, exc) from exc
