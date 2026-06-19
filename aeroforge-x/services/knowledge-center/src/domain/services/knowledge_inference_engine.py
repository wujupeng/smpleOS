from __future__ import annotations

import logging
from typing import Optional

from ..entities.knowledge_graph import KnowledgeGraph
from ..entities.knowledge_link import KnowledgeLink
from ..value_objects.inference_result import InferenceResult
from ..value_objects.link_type import LinkType

logger = logging.getLogger(__name__)


class KnowledgeInferenceEngine:
    def infer_links(
        self,
        graph: KnowledgeGraph,
        input_node_ids: list[str],
        reasoning_type: str = "transitive",
    ) -> InferenceResult:
        result = InferenceResult(
            input_node_ids=input_node_ids,
            reasoning_type=reasoning_type,
        )
        if reasoning_type == "transitive":
            self._transitive_inference(graph, input_node_ids, result)
        elif reasoning_type == "analogical":
            self._analogical_inference(graph, input_node_ids, result)
        elif reasoning_type == "statistical":
            self._statistical_inference(graph, input_node_ids, result)
        else:
            self._rule_based_inference(graph, input_node_ids, result)

        if result.inferred_links:
            confidences = [l["confidence"] for l in result.inferred_links]
            result.confidence = round(sum(confidences) / len(confidences), 4)
        result.explanation = (
            f"Inferred {len(result.inferred_links)} new links using {reasoning_type} reasoning "
            f"from {len(input_node_ids)} input nodes"
        )
        logger.info(f"Knowledge inference: {result.explanation}")
        return result

    def _transitive_inference(
        self, graph: KnowledgeGraph, input_node_ids: list[str], result: InferenceResult
    ) -> None:
        links = graph.get_all_links()
        adjacency: dict[str, list[tuple[str, str, float]]] = {}
        for link in links:
            adjacency.setdefault(link.source_node_id, []).append(
                (link.target_node_id, link.link_type, float(link.confidence))
            )
            if link.bidirectional:
                adjacency.setdefault(link.target_node_id, []).append(
                    (link.source_node_id, link.link_type, float(link.confidence))
                )

        for node_a in input_node_ids:
            neighbors_a = adjacency.get(node_a, [])
            for node_b, link_type_ab, conf_ab in neighbors_a:
                neighbors_b = adjacency.get(node_b, [])
                for node_c, link_type_bc, conf_bc in neighbors_b:
                    if node_c in input_node_ids or node_c == node_a:
                        continue
                    existing = graph.get_all_links()
                    already_exists = any(
                        l.source_node_id == node_a and l.target_node_id == node_c
                        for l in existing
                    )
                    if already_exists:
                        continue
                    inferred_conf = round(conf_ab * conf_bc * 0.7, 4)
                    if inferred_conf >= 0.3:
                        result.add_inferred_link(
                            source_id=node_a,
                            target_id=node_c,
                            link_type=LinkType.AFFECTS.value,
                            confidence=inferred_conf,
                        )

    def _analogical_inference(
        self, graph: KnowledgeGraph, input_node_ids: list[str], result: InferenceResult
    ) -> None:
        nodes = graph.get_all_nodes()
        links = graph.get_all_links()
        for node_id in input_node_ids:
            node = graph.get_node(node_id)
            if not node:
                continue
            similar = [
                n for n in nodes
                if n.node_type == node.node_type
                and n.node_id != node_id
                and any(tag in n.tags for tag in node.tags)
            ]
            for sim_node in similar:
                sim_links = [l for l in links if l.involves_node(sim_node.node_id)]
                for sl in sim_links:
                    other_id = sl.get_other_node(sim_node.node_id)
                    if other_id and other_id not in input_node_ids:
                        existing = any(
                            l.source_node_id == node_id and l.target_node_id == other_id
                            for l in links
                        )
                        if not existing:
                            inferred_conf = round(float(sl.confidence) * 0.5, 4)
                            if inferred_conf >= 0.3:
                                result.add_inferred_link(
                                    source_id=node_id,
                                    target_id=other_id,
                                    link_type=sl.link_type,
                                    confidence=inferred_conf,
                                )

    def _statistical_inference(
        self, graph: KnowledgeGraph, input_node_ids: list[str], result: InferenceResult
    ) -> None:
        links = graph.get_all_links()
        type_pair_counts: dict[tuple[str, str, str], int] = {}
        for link in links:
            src = graph.get_node(link.source_node_id)
            tgt = graph.get_node(link.target_node_id)
            if src and tgt:
                key = (src.node_type, tgt.node_type, link.link_type)
                type_pair_counts[key] = type_pair_counts.get(key, 0) + 1
        total_links = len(links) or 1
        for node_id in input_node_ids:
            node = graph.get_node(node_id)
            if not node:
                continue
            for (src_type, tgt_type, link_type), count in type_pair_counts.items():
                prob = count / total_links
                if prob < 0.05:
                    continue
                if node.node_type == src_type:
                    targets = graph.get_nodes_by_type(tgt_type)
                    for t in targets:
                        if t.node_id not in input_node_ids:
                            existing = any(
                                l.source_node_id == node_id and l.target_node_id == t.node_id
                                for l in links
                            )
                            if not existing and prob >= 0.3:
                                result.add_inferred_link(
                                    source_id=node_id,
                                    target_id=t.node_id,
                                    link_type=link_type,
                                    confidence=round(prob, 4),
                                )

    def _rule_based_inference(
        self, graph: KnowledgeGraph, input_node_ids: list[str], result: InferenceResult
    ) -> None:
        rules = [
            {
                "source_type": "requirement",
                "target_type": "design",
                "link_type": LinkType.DERIVES_FROM.value,
                "confidence": 0.85,
            },
            {
                "source_type": "design",
                "target_type": "structure",
                "link_type": LinkType.IMPLEMENTS.value,
                "confidence": 0.8,
            },
            {
                "source_type": "structure",
                "target_type": "material",
                "link_type": LinkType.USES_MATERIAL.value,
                "confidence": 0.75,
            },
            {
                "source_type": "structure",
                "target_type": "manufacturing",
                "link_type": LinkType.PRODUCED_BY.value,
                "confidence": 0.7,
            },
        ]
        links = graph.get_all_links()
        for node_id in input_node_ids:
            node = graph.get_node(node_id)
            if not node:
                continue
            for rule in rules:
                if node.node_type == rule["source_type"]:
                    targets = graph.get_nodes_by_type(rule["target_type"])
                    for t in targets:
                        if t.node_id not in input_node_ids:
                            existing = any(
                                l.source_node_id == node_id
                                and l.target_node_id == t.node_id
                                and l.link_type == rule["link_type"]
                                for l in links
                            )
                            if not existing:
                                result.add_inferred_link(
                                    source_id=node_id,
                                    target_id=t.node_id,
                                    link_type=rule["link_type"],
                                    confidence=rule["confidence"],
                                )