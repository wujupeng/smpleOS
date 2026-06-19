import asyncpg
import os


class DatabaseConfig:
    POSTGRES_DSN = os.getenv("POSTGRES_DSN", "postgresql://aeroforge:aeroforge@localhost:5432/aeroforge_x")


_pg_pool: asyncpg.Pool | None = None


async def get_pg_pool() -> asyncpg.Pool:
    global _pg_pool
    if _pg_pool is None:
        _pg_pool = await asyncpg.create_pool(
            DatabaseConfig.POSTGRES_DSN,
            min_size=5,
            max_size=20,
            schema="workflow_engine"
        )
    return _pg_pool


async def close_connections():
    global _pg_pool
    if _pg_pool:
        await _pg_pool.close()
        _pg_pool = None