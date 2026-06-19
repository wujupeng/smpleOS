"""AeroForge-X V6.1 IncrementalTopologyPropagationService

BOM incremental topology propagation: O(k·log n) algorithm
replaces O(n²) full-tree recursive refresh. Supports 100K-node
BOM three-view propagation <5 seconds.

REQ-IC-001~010
"""

from __future__ import annotations

import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class EdgeType(str, Enum):
    DERIVATION = "Derivation"
    PROPAGATION = "Propagation"


@dataclass
class BOMNode:
    node_id: str
    parent_ids: list[str] = field(default_factory=list)
    propagation_rules: dict = field(default_factory=dict)
    config_view_type: str = "Design"
    last_propagation_hash: str = ""

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "parent_ids": self.parent_ids,
            "propagation_rules": self.propagation_rules,
            "config_view_type": self.config_view_type,
            "last_propagation_hash": self.last_propagation_hash,
        }


@dataclass
class BOMEdge:
    source_id: str
    target_id: str
    edge_type: EdgeType = EdgeType.DERIVATION
    rule_id: str = ""

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "edge_type": self.edge_type.value,
            "rule_id": self.rule_id,
        }


@dataclass
class AffectedSubtree:
    root_node_id: str
    affected_nodes: list[str] = field(default_factory=list)
    topological_order: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "root_node_id": self.root_node_id,
            "affected_nodes": self.affected_nodes,
            "topological_order": self.topological_order,
        }


@dataclass
class PropagationResult:
    change_id: str
    affected_node_count: int = 0
    propagation_duration_ms: float = 0.0
    is_incremental: bool = True
    fallback_triggered: bool = False
    inconsistent_nodes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "change_id": self.change_id,
            "affected_node_count": self.affected_node_count,
            "propagation_duration_ms": self.propagation_duration_ms,
            "is_incremental": self.is_incremental,
            "fallback_triggered": self.fallback_triggered,
            "inconsistent_nodes": self.inconsistent_nodes,
        }


class IncrementalTopologyPropagationService:

    def __init__(self, repo=None) -> None:
        self._repo = repo
        self._nodes: dict[str, BOMNode] = {}
        self._edges: list[BOMEdge] = []
        self._adjacency: dict[str, list[str]] = {}
        self._propagation_log: list[PropagationResult] = []

    def addNode(self, node: BOMNode) -> None:
        self._nodes[node.node_id] = node
        if node.node_id not in self._adjacency:
            self._adjacency[node.node_id] = []

    def addEdge(self, edge: BOMEdge) -> None:
        self._edges.append(edge)
        if edge.source_id not in self._adjacency:
            self._adjacency[edge.source_id] = []
        self._adjacency[edge.source_id].append(edge.target_id)

    def buildDependencyGraph(self, bom_tree: dict) -> None:
        nodes_data = bom_tree.get("nodes", [])
        edges_data = bom_tree.get("edges", [])

        for n in nodes_data:
            node = BOMNode(
                node_id=n.get("node_id", ""),
                parent_ids=n.get("parent_ids", []),
                propagation_rules=n.get("propagation_rules", {}),
                config_view_type=n.get("config_view_type", "Design"),
            )
            self.addNode(node)

        for e in edges_data:
            edge = BOMEdge(
                source_id=e.get("source_id", ""),
                target_id=e.get("target_id", ""),
                edge_type=EdgeType(e.get("edge_type", "Derivation")),
                rule_id=e.get("rule_id", ""),
            )
            self.addEdge(edge)

    def computeTopologicalOrder(self, changed_node_ids: list[str]) -> AffectedSubtree:
        affected = set()
        queue = deque(changed_node_ids)

        while queue:
            current = queue.popleft()
            if current in affected:
                continue
            affected.add(current)
            for child in self._adjacency.get(current, []):
                if child not in affected:
                    queue.append(child)

        in_degree: dict[str, int] = {n: 0 for n in affected}
        for n in affected:
            for child in self._adjacency.get(n, []):
                if child in affected:
                    in_degree[child] = in_degree.get(child, 0) + 1

        topo_queue = deque([n for n in affected if in_degree.get(n, 0) == 0])
        topo_order = []

        while topo_queue:
            current = topo_queue.popleft()
            topo_order.append(current)
            for child in self._adjacency.get(current, []):
                if child in affected:
                    in_degree[child] -= 1
                    if in_degree[child] == 0:
                        topo_queue.append(child)

        return AffectedSubtree(
            root_node_id=changed_node_ids[0] if changed_node_ids else "",
            affected_nodes=list(affected),
            topological_order=topo_order,
        )

    def propagateIncremental(
        self, changed_node_ids: list[str], change_data: dict
    ) -> PropagationResult:
        start = time.monotonic()
        change_id = f"CHG-{uuid.uuid4().hex[:8]}"

        subtree = self.computeTopologicalOrder(changed_node_ids)

        for node_id in subtree.topological_order:
            node = self._nodes.get(node_id)
            if node is None:
                continue
            node.last_propagation_hash = str(hash(frozenset(change_data.items())))

        elapsed_ms = (time.monotonic() - start) * 1000.0

        result = PropagationResult(
            change_id=change_id,
            affected_node_count=len(subtree.affected_nodes),
            propagation_duration_ms=elapsed_ms,
            is_incremental=True,
        )
        self._propagation_log.append(result)
        return result

    def propagateBatchIncremental(
        self, batch_changes: list[dict]
    ) -> list[PropagationResult]:
        start = time.monotonic()
        results = []

        all_changed_ids = []
        for change in batch_changes:
            node_ids = change.get("changed_node_ids", [])
            all_changed_ids.extend(node_ids)

        if all_changed_ids:
            subtree = self.computeTopologicalOrder(all_changed_ids)
            for node_id in subtree.topological_order:
                node = self._nodes.get(node_id)
                if node is None:
                    continue
                node.last_propagation_hash = str(hash(frozenset(str(batch_changes).items())))

            change_id = f"BCH-{uuid.uuid4().hex[:8]}"
            elapsed_ms = (time.monotonic() - start) * 1000.0
            result = PropagationResult(
                change_id=change_id,
                affected_node_count=len(subtree.affected_nodes),
                propagation_duration_ms=elapsed_ms,
                is_incremental=True,
            )
            results.append(result)
            self._propagation_log.append(result)

        return results

    def getPropagationLog(self) -> list[PropagationResult]:
        return list(self._propagation_log)

    def getNodeCount(self) -> int:
        return len(self._nodes)