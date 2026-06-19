from __future__ import annotations

import uuid
import hashlib
import json
from datetime import datetime, timezone
from typing import Optional

from ..entities.knowledge_graph import KnowledgeGraph
from ..entities.knowledge_node import (
    KnowledgeNode,
    RequirementNode,
    DesignNode,
    StructureNode,
    MaterialNode,
    ManufacturingNode,
    FlightNode,
    MaintenanceNode,
)
from ..entities.knowledge_link import KnowledgeLink
from ..value_objects.node_type import NodeType
from ..value_objects.link_type import LinkType
from ..value_objects.impact_result import ImpactResult
from ..value_objects.inference_result import InferenceResult
from ..value_objects.quality_metrics import QualityMetrics
from ..value_objects.anomaly_report import AnomalyReport
from ..value_objects.graph_snapshot import GraphSnapshot


_NODE_TYPE_MAP = {
    NodeType.REQUIREMENT: RequirementNode,
    NodeType.DESIGN: DesignNode,
    NodeType.STRUCTURE: StructureNode,
    NodeType.MATERIAL: MaterialNode,
    NodeType.MANUFACTURING: ManufacturingNode,
    NodeType.FLIGHT: FlightNode,
    NodeType.MAINTENANCE: MaintenanceNode,
}


class KnowledgeGraphService:
    def __init__(self) -> None:
        self._graphs: dict[str, KnowledgeGraph] = {}

    def create_graph(self, name: str, description: str = "", created_by: str | None = None) -> KnowledgeGraph:
        graph = KnowledgeGraph(
            name=name,
            description=description,
            created_by=created_by,
        )
        self._graphs[graph.graph_id] = graph
        return graph

    def get_graph(self, graph_id: str) -> Optional[KnowledgeGraph]:
        return self._graphs.get(graph_id)

    def create_node(
        self,
        graph_id: str,
        node_type: str,
        name: str,
        properties: dict | None = None,
        tags: list[str] | None = None,
        confidence: float = 1.0,
        source: str = "manual",
        source_ref: str | None = None,
        created_by: str | None = None,
    ) -> KnowledgeNode:
        graph = self._get_graph_or_raise(graph_id)
        nt = NodeType(node_type)
        node_cls = _NODE_TYPE_MAP.get(nt, KnowledgeNode)
        node = node_cls(
            graph_id=graph_id,
            node_type=nt.value,
            name=name,
            properties=properties or {},
            tags=tags or [],
            confidence=confidence,
            source=source,
            source_ref=source_ref,
            created_by=created_by,
        )
        graph.add_node(node)
        return node

    def update_node(self, graph_id: str, node_id: str, **kwargs) -> KnowledgeNode:
        graph = self._get_graph_or_raise(graph_id)
        return graph.update_node(node_id, **kwargs)

    def delete_node(self, graph_id: str, node_id: str) -> None:
        graph = self._get_graph_or_raise(graph_id)
        graph.remove_node(node_id)

    def create_link(
        self,
        graph_id: str,
        source_node_id: str,
        target_node_id: str,
        link_type: str,
        weight: float = 1.0,
        confidence: float = 1.0,
        bidirectional: bool = False,
        properties: dict | None = None,
        created_by: str | None = None,
    ) -> KnowledgeLink:
        graph = self._get_graph_or_raise(graph_id)
        lt = LinkType(link_type)
        link = KnowledgeLink(
            graph_id=graph_id,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            link_type=lt.value,
            weight=weight,
            confidence=confidence,
            bidirectional=bidirectional,
            properties=properties or {},
            created_by=created_by,
        )
        graph.add_link(link)
        return link

    def update_link(self, graph_id: str, link_id: str, **kwargs) -> KnowledgeLink:
        graph = self._get_graph_or_raise(graph_id)
        return graph.update_link(link_id, **kwargs)

    def delete_link(self, graph_id: str, link_id: str) -> None:
        graph = self._get_graph_or_raise(graph_id)
        graph.remove_link(link_id)

    def get_neighbors(self, graph_id: str, node_id: str, depth: int = 1) -> list[KnowledgeNode]:
        graph = self._get_graph_or_raise(graph_id)
        return graph.get_neighbors(node_id, depth)

    def batch_create_nodes(self, graph_id: str, nodes_data: list[dict]) -> list[KnowledgeNode]:
        graph = self._get_graph_or_raise(graph_id)
        created = []
        for nd in nodes_data:
            node = self.create_node(graph_id=graph_id, **nd)
            created.append(node)
        return created

    def batch_create_links(self, graph_id: str, links_data: list[dict]) -> list[KnowledgeLink]:
        graph = self._get_graph_or_raise(graph_id)
        created = []
        for ld in links_data:
            link = self.create_link(graph_id=graph_id, **ld)
            created.append(link)
        return created

    def propagate_impact(self, graph_id: str, source_node_id: str, depth: int = 3) -> ImpactResult:
        graph = self._get_graph_or_raise(graph_id)
        raw = graph.propagate_impact(source_node_id, depth)
        result = ImpactResult(
            source_node_id=source_node_id,
            impact_paths=raw["impact_paths"],
            propagation_depth=depth,
            is_partial=raw["total_affected"] > 1000,
        )
        for node_info in raw["affected_nodes"]:
            result.add_affected_node(
                node_id=node_info["node_id"],
                node_type=node_info["node_type"],
                depth=node_info["depth"],
                confidence=node_info["confidence"],
                path=node_info["path"],
            )
        return result

    def assess_quality(self, graph_id: str) -> QualityMetrics:
        graph = self._get_graph_or_raise(graph_id)
        nodes = graph.get_all_nodes()
        links = graph.get_all_links()
        if not nodes:
            return QualityMetrics()
        typed_nodes = set(n.node_type for n in nodes)
        expected_types = set(NodeType.values())
        completeness = len(typed_nodes) / len(expected_types) if expected_types else 0
        consistent = sum(1 for n in nodes if n.confidence >= 0.5) / len(nodes)
        recent = sum(1 for n in nodes if not n.is_stale(90)) / len(nodes)
        connected = sum(1 for n in nodes if any(l.involves_node(n.node_id) for l in links)) / len(nodes)
        coverage = min(len(nodes) / 100, 1.0)
        freshness = sum(1 for n in nodes if not n.is_stale(30)) / len(nodes)
        return QualityMetrics(
            completeness=round(completeness, 4),
            consistency=round(consistent, 4),
            timeliness=round(recent, 4),
            connectivity=round(connected, 4),
            coverage=round(coverage, 4),
            freshness=round(freshness, 4),
        )

    def detect_anomalies(self, graph_id: str) -> list[AnomalyReport]:
        graph = self._get_graph_or_raise(graph_id)
        nodes = graph.get_all_nodes()
        links = graph.get_all_links()
        anomalies = []
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
        return anomalies

    def create_snapshot(self, graph_id: str, name: str = "", created_by: str | None = None) -> GraphSnapshot:
        graph = self._get_graph_or_raise(graph_id)
        snapshot_data = graph.create_snapshot()
        checksum = hashlib.sha256(
            json.dumps(snapshot_data, default=str, sort_keys=True).encode()
        ).hexdigest()
        return GraphSnapshot(
            graph_id=graph_id,
            graph_version=graph.version,
            name=name or f"snapshot-v{graph.version}",
            node_count=graph.node_count,
            link_count=graph.link_count,
            checksum=checksum,
            snapshot_data=snapshot_data,
            created_by=created_by,
        )

    def _get_graph_or_raise(self, graph_id: str) -> KnowledgeGraph:
        graph = self._graphs.get(graph_id)
        if not graph:
            raise ValueError(f"Graph {graph_id} not found")
        return graph
