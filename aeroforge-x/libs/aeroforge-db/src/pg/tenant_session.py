from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from pydantic_settings import BaseSettings

from aeroforge_common.tenant.context import TenantContext

logger = logging.getLogger(__name__)


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


class TenantBase(DeclarativeBase):
    pass


async def get_tenant_session() -> AsyncGenerator[AsyncSession, None]:
    tenant_info = TenantContext.get()
    async with _async_session_factory() as session:
        try:
            if tenant_info and tenant_info.schema_name != "public":
                await session.execute(
                    text(f"SET search_path TO {tenant_info.schema_name}, public")
                )
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_public_session() -> AsyncGenerator[AsyncSession, None]:
    async with _async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def create_tenant_schema(tenant_code: str) -> bool:
    schema_name = f"tenant_{tenant_code}"
    async with _async_session_factory() as session:
        try:
            await session.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
            await session.execute(text(f"SET search_path TO {schema_name}, public"))
            await session.run_sync(TenantBase.metadata.create_all)
            await session.execute(text("SET search_path TO public"))
            await session.commit()
            logger.info("Created tenant schema: %s", schema_name)
            return True
        except Exception as e:
            await session.rollback()
            logger.error("Failed to create tenant schema %s: %s", schema_name, e)
            return False


async def drop_tenant_schema(tenant_code: str) -> bool:
    schema_name = f"tenant_{tenant_code}"
    async with _async_session_factory() as session:
        try:
            await session.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"))
            await session.commit()
            logger.info("Dropped tenant schema: %s", schema_name)
            return True
        except Exception as e:
            await session.rollback()
            logger.error("Failed to drop tenant schema %s: %s", schema_name, e)
            return False


async def migrate_tenant_schema(tenant_code: str) -> bool:
    schema_name = f"tenant_{tenant_code}"
    async with _async_session_factory() as session:
        try:
            result = await session.execute(
                text("SELECT schema_name FROM information_schema.schemata WHERE schema_name = :name"),
                {"name": schema_name},
            )
            if result.scalar() is None:
                return await create_tenant_schema(tenant_code)

            await session.execute(text(f"SET search_path TO {schema_name}, public"))
            await session.run_sync(TenantBase.metadata.create_all)
            await session.execute(text("SET search_path TO public"))
            await session.commit()
            logger.info("Migrated tenant schema: %s", schema_name)
            return True
        except Exception as e:
            await session.rollback()
            logger.error("Failed to migrate tenant schema %s: %s", schema_name, e)
            return False


async def list_tenant_schemas() -> list[str]:
    async with _async_session_factory() as session:
        result = await session.execute(
            text("SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'tenant_%'")
        )
        return [row[0] for row in result.fetchall()]


async def init_tenant_db() -> None:
    async with _engine.begin() as conn:
        await conn.run_sync(TenantBase.metadata.create_all)


async def close_tenant_db() -> None:
    await _engine.dispose()