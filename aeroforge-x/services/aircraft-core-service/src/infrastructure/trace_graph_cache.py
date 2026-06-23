from __future__ import annotations

import asyncio
import logging
from typing import Optional

from src.domain.models.trace_node import TraceNode
from src.domain.models.trace_edge import TraceEdge

logger = logging.getLogger(__name__)


class TraceGraphCache:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._nodes: dict[str, TraceNode] = {}
        self._adjacency: dict[str, list[TraceEdge]] = {}
        self._reverse_adjacency: dict[str, list[TraceEdge]] = {}

    async def add_node(self, node: TraceNode):
        async with self._lock:
            self._nodes[node.node_id] = node
            if node.node_id not in self._adjacency:
                self._adjacency[node.node_id] = []
            if node.node_id not in self._reverse_adjacency:
                self._reverse_adjacency[node.node_id] = []

    async def add_edge(self, edge: TraceEdge):
        async with self._lock:
            if edge.source_node_id not in self._adjacency:
                self._adjacency[edge.source_node_id] = []
            self._adjacency[edge.source_node_id].append(edge)
            if edge.target_node_id not in self._reverse_adjacency:
                self._reverse_adjacency[edge.target_node_id] = []
            self._reverse_adjacency[edge.target_node_id].append(edge)

    def get_node(self, node_id: str) -> Optional[TraceNode]:
        return self._nodes.get(node_id)

    def get_outgoing(self, node_id: str) -> list[TraceEdge]:
        return self._adjacency.get(node_id, [])

    def get_incoming(self, node_id: str) -> list[TraceEdge]:
        return self._reverse_adjacency.get(node_id, [])

    async def clear(self):
        async with self._lock:
            self._nodes.clear()
            self._adjacency.clear()
            self._reverse_adjacency.clear()

    def node_count(self) -> int:
        return len(self._nodes)

    def edge_count(self) -> int:
        return sum(len(edges) for edges in self._adjacency.values())

    def find_node_by_domain(self, domain: str, domain_id: str) -> Optional[TraceNode]:
        for node in self._nodes.values():
            props = node.properties or {}
            if props.get("domain") == domain and props.get("domain_id") == domain_id:
                return node
        return None


trace_graph_cache = TraceGraphCache()