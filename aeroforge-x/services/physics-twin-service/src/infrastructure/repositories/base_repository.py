"""AeroForge-X Repository Layer - Base Classes

Provides abstract base repository and common patterns for:
- InMemoryRepository: testing fallback
- AsyncpgRepository: production PostgreSQL persistence
- Neo4jRepository: graph persistence for traceability

Design principle: Domain services receive Repository via DI,
enabling testability (in-memory) and production (asyncpg) swap.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, Optional, TypeVar

import asyncpg

T = TypeVar("T")


class BaseRepository(ABC):
    pass


class InMemoryRepository(BaseRepository):
    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    def _put(self, table: str, key: str, data: dict) -> None:
        if table not in self._store:
            self._store[table] = {}
        self._store[table][key] = data

    def _get(self, table: str, key: str) -> Optional[dict]:
        return self._store.get(table, {}).get(key)

    def _list(self, table: str, **filters) -> list[dict]:
        rows = list(self._store.get(table, {}).values())
        for k, v in filters.items():
            rows = [r for r in rows if r.get(k) == v]
        return rows

    def _delete(self, table: str, key: str) -> bool:
        if table in self._store and key in self._store[table]:
            del self._store[table][key]
            return True
        return False


class AsyncpgRepository(BaseRepository):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def _execute(self, query: str, *args) -> str:
        async with self._pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def _fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        async with self._pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def _fetch(self, query: str, *args) -> list[asyncpg.Record]:
        async with self._pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def _fetchval(self, query: str, *args) -> Any:
        async with self._pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    @staticmethod
    def _json_dumps(obj: Any) -> str:
        if obj is None:
            return "null"
        return json.dumps(obj, default=str)

    @staticmethod
    def _json_loads(val: Optional[str]) -> Any:
        if val is None:
            return None
        if isinstance(val, (dict, list)):
            return val
        return json.loads(val)