from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from pydantic_settings import BaseSettings


class PgSettings(BaseSettings):
    database_url: str = "postgresql+asyncpg://aeroforge:aeroforge_dev@localhost:5432/aeroforge_x"
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30

    model_config = {"env_prefix": "PG_"}


_settings = PgSettings()
_engine = create_async_engine(
    _settings.database_url,
    pool_size=_settings.pool_size,
    max_overflow=_settings.max_overflow,
    pool_timeout=_settings.pool_timeout,
    echo=False,
)
_async_session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with _async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    await _engine.dispose()