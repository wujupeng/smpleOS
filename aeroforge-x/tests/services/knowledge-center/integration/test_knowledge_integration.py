import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'services', 'knowledge-center'))

from src.domain.entities.knowledge_graph import KnowledgeGraph
from src.domain.entities.knowledge_node import KnowledgeNode, RequirementNode, DesignNode, StructureNode, MaterialNode, ManufacturingNode
from src.domain.entities.knowledge_link import KnowledgeLink
from src.domain.services.knowledge_graph_service import KnowledgeGraphService
from src.domain.services.impact_propagation_engine import ImpactPropagationEngine
from src.domain.services.knowledge_inference_engine import KnowledgeInferenceEngine
from src.domain.services.knowledge_quality_service import KnowledgeQualityService
from src.domain.services.graph_snapshot_service import GraphSnapshotService


class TestKnowledgeNodeCRUDIntegration:
    def test_create_read_update_delete_node(self):
        svc = KnowledgeGraphService()
        graph = svc.create_graph("Integration Test")
        node = svc.create_node(graph.graph_id, node_type="requirement", name="Wing Span")
        assert svc.get_graph(graph.graph_id).get_node(node.node_id) is not None
        svc.update_node(graph.graph_id, node.node_id, name="Wing Span Updated")
        assert svc.get_graph(graph.graph_id).get_node(node.node_id).name == "Wing Span Updated"
        svc.delete_node(graph.graph_id, node.node_id)
        assert svc.get_graph(graph.graph_id).node_count == 0

    def test_create_read_update_delete_link(self):
        svc = KnowledgeGraphService()
        graph = svc.create_graph("Integration Test")
        n1 = svc.create_node(graph.graph_id, node_type="requirement", name="R1")
        n2 = svc.create_node(graph.graph_id, node_type="design", name="D1")
        link = svc.create_link(graph.graph_id, n1.node_id, n2.node_id, "derives_from")
        assert svc.get_graph(graph.graph_id).link_count == 1
        svc.delete_link(graph.graph_id, link.link_id)
        assert svc.get_graph(graph.graph_id).link_count == 0


class TestImpactPropagationIntegration:
    def test_end_to_end_impact_propagation(self):
        svc = KnowledgeGraphService()
        graph = svc.create_graph("Impact Test")
        n1 = svc.create_node(graph.graph_id, node_type="requirement", name="Wing Span Increase")
        n2 = svc.create_node(graph.graph_id, node_type="design", name="Wing Design")
        n3 = svc.create_node(graph.graph_id, node_type="structure", name="Wing Spar")
        n4 = svc.create_node(graph.graph_id, node_type="material", name="CFRP Material")
        n5 = svc.create_node(graph.graph_id, node_type="manufacturing", name="Autoclave Process")
        svc.create_link(graph.graph_id, n1.node_id, n2.node_id, "derives_from", confidence=0.95)
        svc.create_link(graph.graph_id, n2.node_id, n3.node_id, "implements", confidence=0.9)
        svc.create_link(graph.graph_id, n3.node_id, n4.node_id, "uses_material", confidence=0.85)
        svc.create_link(graph.graph_id, n3.node_id, n5.node_id, "produced_by", confidence=0.8)
        result = svc.propagate_impact(graph.graph_id, n1.node_id, depth=3)
        assert result.total_affected == 4
        assert result.affected_nodes[0]["depth"] == 1
        assert result.affected_nodes[-1]["depth"] == 3

    def test_impact_propagation_with_engine(self):
        graph = KnowledgeGraph(name="Engine Test")
        nodes = [
            KnowledgeNode(node_type="requirement", name=f"R{i}")
            for i in range(5)
        ]
        for n in nodes:
            graph.add_node(n)
        for i in range(4):
            graph.add_link(KnowledgeLink(
                source_node_id=nodes[i].node_id,
                target_node_id=nodes[i + 1].node_id,
                link_type="derives_from",
                confidence=0.9 - i * 0.1,
            ))
        engine = ImpactPropagationEngine()
        result = engine.propagate_impact(graph, nodes[0].node_id, depth=4)
        assert len(result.affected_nodes) == 4
        critical = engine.find_critical_paths(result, threshold=0.5)
        assert len(critical) >= 1


class TestKnowledgeInferenceIntegration:
    def test_transitive_inference_e2e(self):
        graph = KnowledgeGraph(name="Inference Test")
        n1 = KnowledgeNode(node_type="requirement", name="R1")
        n2 = KnowledgeNode(node_type="design", name="D1")
        n3 = KnowledgeNode(node_type="structure", name="S1")
        graph.add_node(n1)
        graph.add_node(n2)
        graph.add_node(n3)
        graph.add_link(KnowledgeLink(source_node_id=n1.node_id, target_node_id=n2.node_id, link_type="derives_from", confidence=0.9))
        graph.add_link(KnowledgeLink(source_node_id=n2.node_id, target_node_id=n3.node_id, link_type="implements", confidence=0.8))
        engine = KnowledgeInferenceEngine()
        result = engine.infer_links(graph, [n1.node_id], reasoning_type="transitive")
        assert len(result.inferred_links) >= 1
        inferred = result.inferred_links[0]
        assert inferred["source_node_id"] == n1.node_id
        assert inferred["target_node_id"] == n3.node_id
        assert inferred["is_inferred"] is True


class TestKnowledgeQualityIntegration:
    def test_quality_assessment_e2e(self):
        graph = KnowledgeGraph(name="Quality Test")
        for ntype in ["requirement", "design", "structure", "material", "manufacturing", "flight", "maintenance"]:
            graph.add_node(KnowledgeNode(node_type=ntype, name=f"{ntype}_node"))
        nodes = graph.get_all_nodes()
        for i in range(len(nodes) - 1):
            graph.add_link(KnowledgeLink(source_node_id=nodes[i].node_id, target_node_id=nodes[i + 1].node_id, link_type="affects"))
        svc = KnowledgeQualityService()
        metrics = svc.assess_quality(graph)
        assert metrics.completeness == 1.0
        assert metrics.connectivity == 1.0
        assert metrics.overall_score > 0.5

    def test_anomaly_detection_e2e(self):
        graph = KnowledgeGraph(name="Anomaly Test")
        graph.add_node(KnowledgeNode(node_type="requirement", name="R1"))
        graph.add_node(KnowledgeNode(node_type="design", name="D1", confidence=0.2))
        svc = KnowledgeQualityService()
        anomalies = svc.detect_anomalies(graph)
        orphan_anomalies = [a for a in anomalies if a.anomaly_type == "orphan"]
        weak_anomalies = [a for a in anomalies if a.anomaly_type == "weak_confidence"]
        assert len(orphan_anomalies) == 2
        assert len(weak_anomalies) == 1


class TestSnapshotIntegration:
    def test_snapshot_create_and_compare(self):
        svc = KnowledgeGraphService()
        graph = svc.create_graph("Snapshot Test")
        svc.create_node(graph.graph_id, node_type="requirement", name="R1")
        snap_svc = GraphSnapshotService()
        g = svc.get_graph(graph.graph_id)
        snap_a = snap_svc.create_snapshot(g, name="v1")
        svc.create_node(graph.graph_id, node_type="design", name="D1")
        snap_b = snap_svc.create_snapshot(g, name="v2")
        diff = snap_svc.compare_snapshots(snap_a, snap_b)
        assert diff["nodes_added"] == 1
        assert snap_a.checksum != snap_b.checksum

    def test_snapshot_checksum_validation(self):
        graph = KnowledgeGraph(name="Checksum Test")
        graph.add_node(KnowledgeNode(node_type="requirement", name="R1"))
        svc = GraphSnapshotService()
        snapshot = svc.create_snapshot(graph, name="test")
        assert len(snapshot.checksum) == 64


class TestCrossCenterEventIntegration:
    def test_knowledge_graph_event_flow(self):
        svc = KnowledgeGraphService()
        graph = svc.create_graph("Event Test")
        n1 = svc.create_node(graph.graph_id, node_type="requirement", name="R1", source="design-center")
        n2 = svc.create_node(graph.graph_id, node_type="design", name="D1", source="design-center")
        link = svc.create_link(graph.graph_id, n1.node_id, n2.node_id, "derives_from")
        result = svc.propagate_impact(graph.graph_id, n1.node_id, depth=3)
        assert result.total_affected >= 1
        metrics = svc.assess_quality(graph.graph_id)
        assert metrics.connectivity == 1.0