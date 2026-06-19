import asyncpg
from neo4j import AsyncGraphDatabase
import os


class DatabaseConfig:
    POSTGRES_DSN = os.getenv("POSTGRES_DSN", "postgresql://aeroforge:aeroforge@localhost:5432/aeroforge_x")
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "aeroforge123")


_pg_pool: asyncpg.Pool | None = None
_neo4j_driver = None


async def get_pg_pool() -> asyncpg.Pool:
    global _pg_pool
    if _pg_pool is None:
        _pg_pool = await asyncpg.create_pool(
            DatabaseConfig.POSTGRES_DSN,
            min_size=5,
            max_size=20,
            schema="aircraft_core"
        )
    return _pg_pool


async def get_neo4j_driver():
    global _neo4j_driver
    if _neo4j_driver is None:
        _neo4j_driver = AsyncGraphDatabase.driver(
            DatabaseConfig.NEO4J_URI,
            auth=(DatabaseConfig.NEO4J_USER, DatabaseConfig.NEO4J_PASSWORD)
        )
    return _neo4j_driver


async def close_connections():
    global _pg_pool, _neo4j_driver
    if _pg_pool:
        await _pg_pool.close()
        _pg_pool = None
    if _neo4j_driver:
        await _neo4j_driver.close()
        _neo4j_driver = None