from __future__ import annotations

import logging
from typing import Optional

from ..entities.knowledge_graph import KnowledgeGraph
from ..entities.knowledge_node import KnowledgeNode
from ..value_objects.quality_metrics import QualityMetrics
from ..value_objects.anomaly_report import AnomalyReport

logger = logging.getLogger(__name__)


class KnowledgeQualityService:
    def assess_quality(self, graph: KnowledgeGraph) -> QualityMetrics:
        nodes = graph.get_all_nodes()
        links = graph.get_all_links()
        if not nodes:
            return QualityMetrics()
        from ..value_objects.node_type import NodeType
        expected_types = set(NodeType.values())
        present_types = set(n.node_type for n in nodes)
        completeness = len(present_types & expected_types) / len(expected_types) if expected_types else 0
        consistent = sum(1 for n in nodes if n.confidence >= 0.5) / len(nodes)
        recent = sum(1 for n in nodes if not n.is_stale(90)) / len(nodes)
        connected_ids = set()
        for l in links:
            connected_ids.add(l.source_node_id)
            connected_ids.add(l.target_node_id)
        connected = sum(1 for n in nodes if n.node_id in connected_ids) / len(nodes)
        coverage = min(len(nodes) / 100, 1.0)
        freshness = sum(1 for n in nodes if not n.is_stale(30)) / len(nodes)
        metrics = QualityMetrics(
            completeness=round(completeness, 4),
            consistency=round(consistent, 4),
            timeliness=round(recent, 4),
            connectivity=round(connected, 4),
            coverage=round(coverage, 4),
            freshness=round(freshness, 4),
        )
        logger.info(f"Knowledge quality assessed: overall={metrics.overall_score}")
        return metrics

    def detect_anomalies(self, graph: KnowledgeGraph) -> list[AnomalyReport]:
        nodes = graph.get_all_nodes()
        links = graph.get_all_links()
        anomalies: list[AnomalyReport] = []
        connected_ids = set()
        for l in links:
            connected_ids.add(l.source_node_id)
            connected_ids.add(l.target_node_id)
        for n in nodes:
            if n.node_id not in connected_ids:
                anomalies.append(AnomalyReport(
                    anomaly_type="orphan",
                    affected_node_ids=[n.node_id],
                    severity="medium",
                    description=f"Orphan node: {n.name} ({n.node_type}) has no connections",
                    remediation="Add relationships or remove if no longer relevant",
                ))
            if n.is_stale(180):
                anomalies.append(AnomalyReport(
                    anomaly_type="stale",
                    affected_node_ids=[n.node_id],
                    severity="low",
                    description=f"Stale node: {n.name} not updated in 180 days",
                    remediation="Review and update or archive",
                ))
            if n.confidence < 0.3:
                anomalies.append(AnomalyReport(
                    anomaly_type="weak_confidence",
                    affected_node_ids=[n.node_id],
                    severity="high",
                    description=f"Low confidence node: {n.name} (confidence={n.confidence})",
                    remediation="Verify source data and update confidence",
                ))
        self._detect_contradictions(graph, anomalies)
        self._detect_circular_dependencies(graph, anomalies)
        logger.info(f"Detected {len(anomalies)} anomalies")
        return anomalies

    def resolve_anomaly(self, anomaly: AnomalyReport, action: str = "acknowledge") -> AnomalyReport:
        if action == "acknowledge":
            anomaly.acknowledge()
        elif action == "resolve":
            anomaly.resolve(resolved_by="system")
        elif action == "dismiss":
            anomaly.dismiss()
        return anomaly

    def _detect_contradictions(self, graph: KnowledgeGraph, anomalies: list[AnomalyReport]) -> None:
        links = graph.get_all_links()
        for i, link_a in enumerate(links):
            for link_b in links[i + 1:]:
                if (link_a.source_node_id == link_b.source_node_id
                        and link_a.target_node_id == link_b.target_node_id
                        and link_a.link_type != link_b.link_type
                        and not link_a.bidirectional and not link_b.bidirectional):
                    anomalies.append(AnomalyReport(
                        anomaly_type="contradiction",
                        affected_node_ids=[link_a.source_node_id, link_a.target_node_id],
                        severity="high",
                        description=f"Contradictory links between {link_a.source_node_id} and {link_a.target_node_id}",
                        remediation="Review and resolve conflicting relationships",
                    ))

    def _detect_circular_dependencies(self, graph: KnowledgeGraph, anomalies: list[AnomalyReport]) -> None:
        links = graph.get_all_links()
        adj: dict[str, list[str]] = {}
        for l in links:
            adj.setdefault(l.source_node_id, []).append(l.target_node_id)

        def has_cycle(node: str, visited: set, rec_stack: set) -> list[str] | None:
            visited.add(node)
            rec_stack.add(node)
            for neighbor in adj.get(node, []):
                if neighbor not in visited:
                    cycle = has_cycle(neighbor, visited, rec_stack)
                    if cycle:
                        return cycle
                elif neighbor in rec_stack:
                    return [node, neighbor]
            rec_stack.discard(node)
            return None

        visited: set[str] = set()
        for node_id in adj:
            if node_id not in visited:
                cycle = has_cycle(node_id, visited, set())
                if cycle:
                    anomalies.append(AnomalyReport(
                        anomaly_type="circular",
                        affected_node_ids=cycle,
                        severity="medium",
                        description=f"Circular dependency detected involving nodes: {cycle}",
                        remediation="Break circular dependency by removing or redirecting a link",
                    ))