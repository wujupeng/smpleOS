from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from neo4j import AsyncDriver, AsyncSession

from aeroforge_common.tenant.context import TenantContext

from .connection import get_driver

logger = logging.getLogger(__name__)


@asynccontextmanager
async def get_tenant_session() -> AsyncGenerator[AsyncSession, None]:
    driver = await get_driver()
    tenant_info = TenantContext.get()
    async with driver.session() as session:
        if tenant_info:
            label = f"Tenant_{tenant_info.tenant_id}"
            await session.run(
                "CALL apoc.cypher.runFragment('MATCH (n) SET n._tenant_id = $tid', {tid: $tid})",
                tid=tenant_info.tenant_id,
            )
        yield session


def add_tenant_filter(cypher: str, tenant_id: str, node_var: str = "n") -> str:
    label = f"Tenant_{tenant_id}"
    if "WHERE" in cypher.upper():
        return cypher.replace(
            "WHERE", f"WHERE {node_var}:{label} AND", 1
        )
    match_pos = cypher.upper().find("MATCH")
    if match_pos >= 0:
        return cypher.replace("MATCH", f"MATCH {node_var}:{label},", 1)
    return cypher


def add_tenant_label_query(node_var: str, tenant_id: str) -> str:
    return f"SET {node_var}:Tenant_{tenant_id}"


async def create_tenant_constraints(tenant_id: str) -> None:
    driver = await get_driver()
    label = f"Tenant_{tenant_id}"
    async with driver.session() as session:
        await session.run(
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.tenant_id IS NOT NULL"
        )
        logger.info("Created Neo4j tenant constraints for %s", tenant_id)


async def remove_tenant_data(tenant_id: str) -> None:
    driver = await get_driver()
    label = f"Tenant_{tenant_id}"
    async with driver.session() as session:
        await session.run(f"MATCH (n:{label}) DETACH DELETE n")
        logger.info("Removed Neo4j tenant data for %s", tenant_id)