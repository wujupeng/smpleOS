from __future__ import annotations

import logging
from collections import deque
from typing import Optional

import asyncpg

from src.infrastructure.repositories.trace_node_repository import TraceNodeRepository
from src.infrastructure.repositories.trace_edge_repository import TraceEdgeRepository
from src.infrastructure.trace_graph_cache import trace_graph_cache, TraceGraphCache
from src.domain.models.trace_node import TraceNode
from src.domain.models.trace_edge import TraceEdge

logger = logging.getLogger(__name__)


class TraceGraphService:
    def __init__(self, pool: asyncpg.Pool):
        self._node_repo = TraceNodeRepository(pool)
        self._edge_repo = TraceEdgeRepository(pool)
        self._cache = trace_graph_cache

    async def create_trace_node(self, identity_id: Optional[str], node_type: str, label: str, properties: Optional[dict] = None) -> TraceNode:
        props = properties or {}
        node = await self._node_repo.create(identity_id, node_type, label, props)
        await self._cache.add_node(node)
        return node

    async def create_trace_edge(self, source_node_id: str, target_node_id: str, edge_type: str, properties: Optional[dict] = None) -> TraceEdge:
        edge = await self._edge_repo.create(source_node_id, target_node_id, edge_type, properties)
        await self._cache.add_edge(edge)
        return edge

    async def trace_query(self, start_node_id: str, direction: str = "both", max_depth: int = 5, max_nodes: int = 100) -> dict:
        visited_nodes: dict[str, TraceNode] = {}
        visited_edges: list[TraceEdge] = []
        queue = deque([(start_node_id, 0)])
        visited_ids: set[str] = {start_node_id}
        truncated = False

        start_node = self._cache.get_node(start_node_id)
        if start_node is None:
            start_node = await self._node_repo.find_by_id(start_node_id)
        if start_node is None:
            return {"nodes": [], "edges": [], "truncated": False}
        visited_nodes[start_node_id] = start_node

        while queue:
            node_id, depth = queue.popleft()
            if depth >= max_depth:
                continue
            edges = []
            if direction in ("outgoing", "both"):
                edges.extend(self._cache.get_outgoing(node_id))
            if direction in ("incoming", "both"):
                edges.extend(self._cache.get_incoming(node_id))
            for edge in edges:
                visited_edges.append(edge)
                next_id = edge.target_node_id if edge.source_node_id == node_id else edge.source_node_id
                if next_id not in visited_ids:
                    if len(visited_nodes) >= max_nodes:
                        truncated = True
                        break
                    visited_ids.add(next_id)
                    next_node = self._cache.get_node(next_id)
                    if next_node is None:
                        next_node = await self._node_repo.find_by_id(next_id)
                    if next_node:
                        visited_nodes[next_id] = next_node
                        queue.append((next_id, depth + 1))
            if truncated:
                break

        return {
            "nodes": [n.to_dict() for n in visited_nodes.values()],
            "edges": [e.to_dict() for e in visited_edges],
            "truncated": truncated,
        }

    async def impact_analysis(self, start_node_id: str, max_depth: int = 5) -> dict:
        direct = []
        indirect = []
        visited: set[str] = {start_node_id}
        queue = deque([(start_node_id, 0)])

        while queue:
            node_id, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for edge in self._cache.get_outgoing(node_id):
                next_id = edge.target_node_id
                if next_id not in visited:
                    visited.add(next_id)
                    node = self._cache.get_node(next_id)
                    if node:
                        entry = {"node": node.to_dict(), "edge_type": edge.edge_type}
                        if depth == 0:
                            direct.append(entry)
                        else:
                            indirect.append(entry)
                        queue.append((next_id, depth + 1))

        return {"direct": direct, "indirect": indirect}

    async def dependency_query(self, start_node_id: str, max_depth: int = 5) -> dict:
        dependencies = []
        visited: set[str] = {start_node_id}
        queue = deque([(start_node_id, 0)])

        while queue:
            node_id, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for edge in self._cache.get_incoming(node_id):
                next_id = edge.source_node_id
                if next_id not in visited:
                    visited.add(next_id)
                    node = self._cache.get_node(next_id)
                    if node:
                        dependencies.append({"node": node.to_dict(), "edge_type": edge.edge_type})
                        queue.append((next_id, depth + 1))

        return {"dependencies": dependencies}

    async def rebuild_graph(self) -> dict:
        await self._edge_repo.delete_all()
        await self._node_repo.delete_all()
        await self._cache.clear()

        from src.infrastructure.database import get_pg_pool
        pool = await get_pg_pool()

        node_count = 0
        edge_count = 0

        blocks = await pool.fetch("SELECT block_id, aircraft_type, block_name FROM block_configurations")
        for b in blocks:
            node = await self.create_trace_node(None, "block", b["block_name"], {"domain": "block", "domain_id": b["block_id"]})
            node_count += 1

        materials = await pool.fetch("SELECT lot_id, material_code, material_name FROM dt_material_lots")
        for m in materials:
            node = await self.create_trace_node(None, "material_lot", m["material_name"], {"domain": "material_lot", "domain_id": m["lot_id"]})
            node_count += 1

            block_mats = await pool.fetch("SELECT block_id FROM dt_block_materials WHERE lot_id = $1", m["lot_id"])
            for bm in block_mats:
                block_node = self._cache.find_node_by_domain("block", bm["block_id"])
                if block_node:
                    await self.create_trace_edge(block_node.node_id, node.node_id, "contains_material")
                    edge_count += 1

        ndts = await pool.fetch("SELECT ndt_record_id, material_lot_id, test_type, result FROM dt_ndt_records")
        for n in ndts:
            node = await self.create_trace_node(None, "ndt_record", f"NDT-{n['test_type']}", {"domain": "ndt_record", "domain_id": str(n["ndt_record_id"])})
            node_count += 1
            mat_node = self._cache.find_node_by_domain("material_lot", n["material_lot_id"])
            if mat_node:
                await self.create_trace_edge(mat_node.node_id, node.node_id, "tested_by")
                edge_count += 1

        cars = await pool.fetch("SELECT car_id, ndt_record_id, description, status FROM dt_corrective_actions")
        for c in cars:
            node = await self.create_trace_node(None, "car", c["description"][:80], {"domain": "car", "domain_id": str(c["car_id"])})
            node_count += 1
            ndt_node = self._cache.find_node_by_domain("ndt_record", str(c["ndt_record_id"]))
            if ndt_node:
                await self.create_trace_edge(ndt_node.node_id, node.node_id, "corrected_by")
                edge_count += 1

        logger.info(f"Graph rebuild complete: {node_count} nodes, {edge_count} edges")
        return {"nodes": node_count, "edges": edge_count}

    async def get_statistics(self) -> dict:
        nodes = await self._node_repo.find_all(limit=10000)
        edges = await self._edge_repo.find_all(limit=10000)
        node_types: dict[str, int] = {}
        edge_types: dict[str, int] = {}
        for n in nodes:
            node_types[n.node_type] = node_types.get(n.node_type, 0) + 1
        for e in edges:
            edge_types[e.edge_type] = edge_types.get(e.edge_type, 0) + 1
        return {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "node_types": node_types,
            "edge_types": edge_types,
            "cache_nodes": self._cache.node_count(),
            "cache_edges": self._cache.edge_count(),
        }

    async def load_cache_from_db(self):
        nodes = await self._node_repo.find_all(limit=10000)
        edges = await self._edge_repo.find_all(limit=10000)
        await self._cache.clear()
        for n in nodes:
            await self._cache.add_node(n)
        for e in edges:
            await self._cache.add_edge(e)
        logger.info(f"Trace graph cache loaded: {len(nodes)} nodes, {len(edges)} edges")


_trace_graph_service: TraceGraphService | None = None


async def get_trace_graph_service() -> TraceGraphService:
    global _trace_graph_service
    if _trace_graph_service is not None:
        return _trace_graph_service
    from src.infrastructure.database import get_pg_pool
    pool = await get_pg_pool()
    _trace_graph_service = TraceGraphService(pool)
    return _trace_graph_service