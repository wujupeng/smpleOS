import asyncpg
import os


class DatabaseConfig:
    POSTGRES_DSN = os.getenv("DATABASE_URL", os.getenv("POSTGRES_DSN", "postgresql://postgres:aeroforge@localhost:5432/aeroforge"))
    TIMESCALE_DSN = os.getenv("TIMESCALEDB_URL", os.getenv("TIMESCALE_DSN", "postgresql://postgres:aeroforge_ts@localhost:5433/aeroforge_ts"))


_pg_pool: asyncpg.Pool | None = None
_ts_pool: asyncpg.Pool | None = None


async def get_pg_pool() -> asyncpg.Pool:
    global _pg_pool
    if _pg_pool is None:
        _pg_pool = await asyncpg.create_pool(
            DatabaseConfig.POSTGRES_DSN,
            min_size=5,
            max_size=20,
            server_settings={"search_path": "physics_twin,public"},
        )
    return _pg_pool


async def get_timescale_pool() -> asyncpg.Pool:
    global _ts_pool
    if _ts_pool is None:
        _ts_pool = await asyncpg.create_pool(
            DatabaseConfig.TIMESCALE_DSN,
            min_size=5,
            max_size=20
        )
    return _ts_pool


async def close_connections():
    global _pg_pool, _ts_pool
    if _pg_pool:
        await _pg_pool.close()
        _pg_pool = None
    if _ts_pool:
        await _ts_pool.close()
        _ts_pool = None