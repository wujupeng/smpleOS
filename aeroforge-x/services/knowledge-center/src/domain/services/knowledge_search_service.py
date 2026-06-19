from __future__ import annotations

import logging
import math
from typing import Optional

from ..entities.knowledge_graph import KnowledgeGraph
from ..entities.knowledge_node import KnowledgeNode

logger = logging.getLogger(__name__)


class KnowledgeSearchService:
    def semantic_search(
        self,
        graph: KnowledgeGraph,
        query_embedding: list[float],
        top_k: int = 10,
        node_type: str | None = None,
        min_confidence: float = 0.0,
    ) -> list[tuple[KnowledgeNode, float]]:
        nodes = graph.get_all_nodes()
        if node_type:
            nodes = [n for n in nodes if n.node_type == node_type]
        nodes = [n for n in nodes if n.confidence >= min_confidence and n.embedding is not None]
        scored = []
        for node in nodes:
            similarity = self._cosine_similarity(query_embedding, node.embedding)
            if similarity > 0:
                scored.append((node, similarity))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def keyword_search(
        self,
        graph: KnowledgeGraph,
        query: str,
        top_k: int = 20,
        node_type: str | None = None,
        tags: list[str] | None = None,
    ) -> list[tuple[KnowledgeNode, float]]:
        nodes = graph.get_all_nodes()
        if node_type:
            nodes = [n for n in nodes if n.node_type == node_type]
        if tags:
            nodes = [n for n in nodes if any(t in n.tags for t in tags)]
        query_lower = query.lower()
        scored = []
        for node in nodes:
            score = 0.0
            if query_lower in node.name.lower():
                score += 1.0
            for tag in node.tags:
                if query_lower in tag.lower():
                    score += 0.5
            for val in node.properties.values():
                if isinstance(val, str) and query_lower in val.lower():
                    score += 0.3
            if score > 0:
                scored.append((node, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def hybrid_search(
        self,
        graph: KnowledgeGraph,
        query: str,
        query_embedding: list[float] | None = None,
        top_k: int = 10,
        node_type: str | None = None,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
    ) -> list[tuple[KnowledgeNode, float]]:
        keyword_results = self.keyword_search(graph, query, top_k=top_k * 3, node_type=node_type)
        keyword_scores = {n.node_id: s for n, s in keyword_results}
        semantic_scores: dict[str, float] = {}
        if query_embedding:
            semantic_results = self.semantic_search(graph, query_embedding, top_k=top_k * 3, node_type=node_type)
            semantic_scores = {n.node_id: s for n, s in semantic_results}
        all_node_ids = set(keyword_scores.keys()) | set(semantic_scores.keys())
        combined = []
        for node_id in all_node_ids:
            node = graph.get_node(node_id)
            if not node:
                continue
            k_score = keyword_scores.get(node_id, 0.0)
            s_score = semantic_scores.get(node_id, 0.0)
            combined_score = keyword_weight * k_score + semantic_weight * s_score
            combined.append((node, combined_score))
        combined.sort(key=lambda x: x[1], reverse=True)
        return combined[:top_k]

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        if len(a) != len(b) or not a:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        mag_a = math.sqrt(sum(x * x for x in a))
        mag_b = math.sqrt(sum(x * x for x in b))
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)