from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
from pydantic_settings import BaseSettings


class Neo4jSettings(BaseSettings):
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "aeroforge_dev"
    neo4j_max_connection_pool_size: int = 50
    neo4j_connection_timeout: int = 30

    model_config = {"env_prefix": ""}


_settings = Neo4jSettings()
_driver: AsyncDriver | None = None


async def get_driver() -> AsyncDriver:
    global _driver
    if _driver is None:
        _driver = AsyncGraphDatabase.driver(
            _settings.neo4j_uri,
            auth=(_settings.neo4j_user, _settings.neo4j_password),
            max_connection_pool_size=_settings.neo4j_max_connection_pool_size,
            connection_timeout=_settings.neo4j_connection_timeout,
        )
    return _driver


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    driver = await get_driver()
    async with driver.session() as session:
        yield session


async def close_driver() -> None:
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None