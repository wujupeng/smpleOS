from __future__ import annotations

import logging
from typing import Optional

from ..entities.knowledge_graph import KnowledgeGraph
from ..entities.knowledge_node import KnowledgeNode
from ..entities.knowledge_link import KnowledgeLink
from ..value_objects.impact_result import ImpactResult
from ..value_objects.link_type import LinkType

logger = logging.getLogger(__name__)

_MAX_NODES = 1000
_CONFIDENCE_DECAY = 0.8
_DEFAULT_DEPTH = 3


class ImpactPropagationEngine:
    def __init__(self, confidence_decay: float = _CONFIDENCE_DECAY, max_nodes: int = _MAX_NODES):
        self._confidence_decay = confidence_decay
        self._max_nodes = max_nodes

    def propagate_impact(
        self,
        graph: KnowledgeGraph,
        source_node_id: str,
        depth: int = _DEFAULT_DEPTH,
        link_types: list[str] | None = None,
    ) -> ImpactResult:
        if not graph.get_node(source_node_id):
            raise ValueError(f"Source node {source_node_id} not found in graph")

        result = ImpactResult(
            source_node_id=source_node_id,
            propagation_depth=depth,
        )
        visited = {source_node_id}
        queue = [(source_node_id, [], 0)]
        processed = 0

        while queue:
            current_id, path, current_depth = queue.pop(0)
            if current_depth >= depth:
                continue
            if processed >= self._max_nodes:
                result.is_partial = True
                result.warnings.append(
                    f"Impact propagation stopped at {self._max_nodes} nodes"
                )
                break

            links = graph.get_all_links()
            for link in links:
                if link_types and link.link_type not in link_types:
                    continue
                neighbor_id = None
                if link.source_node_id == current_id and link.target_node_id not in visited:
                    neighbor_id = link.target_node_id
                elif link.target_node_id == current_id and link.source_node_id not in visited:
                    if not link.bidirectional:
                        continue
                    neighbor_id = link.source_node_id

                if neighbor_id and neighbor_id not in visited:
                    neighbor_node = graph.get_node(neighbor_id)
                    if not neighbor_node:
                        continue
                    visited.add(neighbor_id)
                    processed += 1
                    new_path = path + [link.link_type]
                    confidence = float(link.confidence) * (self._confidence_decay ** current_depth)
                    result.add_affected_node(
                        node_id=neighbor_id,
                        node_type=neighbor_node.node_type,
                        depth=current_depth + 1,
                        confidence=round(confidence, 6),
                        path=new_path,
                    )
                    result.impact_paths.append(new_path)
                    queue.append((neighbor_id, new_path, current_depth + 1))

        logger.info(
            f"Impact propagation from {source_node_id}: "
            f"{len(result.affected_nodes)} nodes affected, "
            f"partial={result.is_partial}"
        )
        return result

    def compute_cascade_score(self, result: ImpactResult) -> float:
        if not result.affected_nodes:
            return 0.0
        total = sum(
            n["confidence"] * (self._confidence_decay ** n["depth"])
            for n in result.affected_nodes
        )
        return round(total, 6)

    def find_critical_paths(self, result: ImpactResult, threshold: float = 0.7) -> list[dict]:
        critical = []
        for node_info in result.affected_nodes:
            if node_info["confidence"] >= threshold:
                critical.append({
                    "node_id": node_info["node_id"],
                    "node_type": node_info["node_type"],
                    "confidence": node_info["confidence"],
                    "depth": node_info["depth"],
                    "path": node_info["path"],
                })
        return sorted(critical, key=lambda x: x["confidence"], reverse=True)