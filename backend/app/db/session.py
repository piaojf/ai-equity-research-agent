"""Async SQLAlchemy engine and explicit transaction boundaries."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.errors import AppError
from app.db.base import Base
from app.db.errors import database_app_error


def normalize_database_url(url: str) -> str:
    """Normalize common sync URLs to an async SQLAlchemy driver URL."""

    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("sqlite://"):
        return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return url


class Database:
    """Own an async engine and expose commit/rollback as one unit of work."""

    def __init__(self, url: str, *, echo: bool = False) -> None:
        self.url = normalize_database_url(url)
        self.engine: AsyncEngine = create_async_engine(
            self.url,
            echo=echo,
            pool_pre_ping=True,
        )
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Yield a session without implicitly committing caller work."""

        async with self.session_factory() as session:
            yield session

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[AsyncSession]:
        """Commit on success and roll back on every failure."""

        async with self.session_factory() as session:
            try:
                async with session.begin():
                    yield session
            except AppError:
                await session.rollback()
                raise
            except SQLAlchemyError as exc:
                await session.rollback()
                raise database_app_error("transaction", exc) from exc

    async def create_schema(self) -> None:
        """Create metadata for local tests and development fixtures."""

        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def drop_schema(self) -> None:
        """Drop metadata for isolated local test databases."""

        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)

    async def dispose(self) -> None:
        await self.engine.dispose()


async def get_session(database: Database) -> AsyncIterator[AsyncSession]:
    """FastAPI-compatible dependency; services decide transaction scope."""

    async with database.session() as session:
        yield session
