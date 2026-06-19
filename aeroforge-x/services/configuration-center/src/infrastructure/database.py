import os
from typing import Optional

import asyncpg


class Database:
    def __init__(self):
        self._pool: Optional[asyncpg.Pool] = None
        self._url = os.getenv(
            "DATABASE_URL",
            "postgresql://aeroforge:aeroforge_dev@postgres:5432/aeroforge_x",
        )

    async def connect(self):
        self._pool = await asyncpg.create_pool(self._url, min_size=5, max_size=20)

    async def disconnect(self):
        if self._pool:
            await self._pool.close()

    def is_connected(self) -> bool:
        return self._pool is not None

    def get_pool(self) -> asyncpg.Pool:
        if not self._pool:
            raise RuntimeError("Database pool not initialized")
        return self._pool

    async def fetch(self, query: str, *args):
        async with self._pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args):
        async with self._pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args):
        async with self._pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    async def execute(self, query: str, *args):
        async with self._pool.acquire() as conn:
            return await conn.execute(query, *args)