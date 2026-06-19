import os
from typing import Optional

from neo4j import AsyncGraphDatabase, AsyncDriver


class Neo4jClient:
    def __init__(self):
        self._driver: Optional[AsyncDriver] = None
        self._uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
        self._user = os.getenv("NEO4J_USER", "neo4j")
        self._password = os.getenv("NEO4J_PASSWORD", "aeroforge_dev")
        self._max_connection_pool_size = int(
            os.getenv("NEO4J_MAX_POOL_SIZE", "50")
        )

    async def connect(self):
        self._driver = AsyncGraphDatabase.driver(
            self._uri,
            auth=(self._user, self._password),
            max_connection_pool_size=self._max_connection_pool_size,
        )

    async def disconnect(self):
        if self._driver:
            await self._driver.close()

    def is_connected(self) -> bool:
        return self._driver is not None

    def get_driver(self) -> AsyncDriver:
        if not self._driver:
            raise RuntimeError("Neo4j driver not initialized")
        return self._driver

    async def execute_read(self, query: str, parameters: dict = None):
        async with self._driver.session() as session:
            result = await session.execute_read(
                lambda tx: tx.run(query, parameters or {})
            )
            records = await result.data()
            return records

    async def execute_write(self, query: str, parameters: dict = None):
        async with self._driver.session() as session:
            result = await session.execute_write(
                lambda tx: tx.run(query, parameters or {})
            )
            summary = await result.consume()
            return summary.counters

    async def run_cypher(self, query: str, parameters: dict = None):
        async with self._driver.session() as session:
            result = await session.run(query, parameters or {})
            records = []
            async for record in result:
                records.append(dict(record))
            return records