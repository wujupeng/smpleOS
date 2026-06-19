import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'services', 'knowledge-center'))

from src.domain.entities.knowledge_graph import KnowledgeGraph
from src.domain.entities.knowledge_node import (
    KnowledgeNode, RequirementNode, DesignNode, StructureNode,
    MaterialNode, ManufacturingNode, FlightNode, MaintenanceNode,
)
from src.domain.entities.knowledge_link import KnowledgeLink
from src.domain.value_objects.node_type import NodeType
from src.domain.value_objects.link_type import LinkType
from src.domain.value_objects.impact_result import ImpactResult
from src.domain.value_objects.inference_result import InferenceResult
from src.domain.value_objects.quality_metrics import QualityMetrics
from src.domain.value_objects.anomaly_report import AnomalyReport
from src.domain.services.knowledge_graph_service import KnowledgeGraphService
from src.domain.services.impact_propagation_engine import ImpactPropagationEngine
from src.domain.services.knowledge_inference_engine import KnowledgeInferenceEngine
from src.domain.services.knowledge_quality_service import KnowledgeQualityService
from src.domain.services.knowledge_search_service import KnowledgeSearchService
from src.domain.services.graph_snapshot_service import GraphSnapshotService


class TestKnowledgeGraph:
    def test_create_graph(self):
        graph = KnowledgeGraph(name="Test Graph")
        assert graph.name == "Test Graph"
        assert graph.version == 1
        assert graph.node_count == 0

    def test_add_node(self):
        graph = KnowledgeGraph(name="Test")
        node = KnowledgeNode(node_type="requirement", name="Wing Span")
        graph.add_node(node)
        assert graph.node_count == 1
        assert graph.get_node(node.node_id) is not None

    def test_add_duplicate_node_raises(self):
        graph = KnowledgeGraph(name="Test")
        node = KnowledgeNode(node_type="requirement", name="Test")
        graph.add_node(node)
        with pytest.raises(ValueError):
            graph.add_node(node)

    def test_remove_node(self):
        graph = KnowledgeGraph(name="Test")
        node = KnowledgeNode(node_type="requirement", name="Test")
        graph.add_node(node)
        graph.remove_node(node.node_id)
        assert graph.node_count == 0

    def test_remove_nonexistent_node_raises(self):
        graph = KnowledgeGraph(name="Test")
        with pytest.raises(ValueError):
            graph.remove_node("nonexistent")

    def test_update_node(self):
        graph = KnowledgeGraph(name="Test")
        node = KnowledgeNode(node_type="requirement", name="Old Name")
        graph.add_node(node)
        updated = graph.update_node(node.node_id, name="New Name")
        assert updated.name == "New Name"
        assert updated.version == 2

    def test_add_link(self):
        graph = KnowledgeGraph(name="Test")
        n1 = KnowledgeNode(node_type="requirement", name="R1")
        n2 = KnowledgeNode(node_type="design", name="D1")
        graph.add_node(n1)
        graph.add_node(n2)
        link = KnowledgeLink(source_node_id=n1.node_id, target_node_id=n2.node_id, link_type="derives_from")
        graph.add_link(link)
        assert graph.link_count == 1

    def test_add_link_missing_node_raises(self):
        graph = KnowledgeGraph(name="Test")
        n1 = KnowledgeNode(node_type="requirement", name="R1")
        graph.add_node(n1)
        link = KnowledgeLink(source_node_id=n1.node_id, target_node_id="missing", link_type="derives_from")
        with pytest.raises(ValueError):
            graph.add_link(link)

    def test_get_neighbors(self):
        graph = KnowledgeGraph(name="Test")
        n1 = KnowledgeNode(node_type="requirement", name="R1")
        n2 = KnowledgeNode(node_type="design", name="D1")
        n3 = KnowledgeNode(node_type="structure", name="S1")
        graph.add_node(n1)
        graph.add_node(n2)
        graph.add_node(n3)
        graph.add_link(KnowledgeLink(source_node_id=n1.node_id, target_node_id=n2.node_id, link_type="derives_from"))
        graph.add_link(KnowledgeLink(source_node_id=n2.node_id, target_node_id=n3.node_id, link_type="implements"))
        neighbors = graph.get_neighbors(n1.node_id, depth=1)
        assert len(neighbors) == 1
        neighbors = graph.get_neighbors(n1.node_id, depth=2)
        assert len(neighbors) == 2

    def test_propagate_impact(self):
        graph = KnowledgeGraph(name="Test")
        n1 = KnowledgeNode(node_type="requirement", name="R1")
        n2 = KnowledgeNode(node_type="design", name="D1")
        n3 = KnowledgeNode(node_type="structure", name="S1")
        graph.add_node(n1)
        graph.add_node(n2)
        graph.add_node(n3)
        graph.add_link(KnowledgeLink(source_node_id=n1.node_id, target_node_id=n2.node_id, link_type="derives_from", confidence=0.9))
        graph.add_link(KnowledgeLink(source_node_id=n2.node_id, target_node_id=n3.node_id, link_type="implements", confidence=0.8))
        result = graph.propagate_impact(n1.node_id, depth=3)
        assert result["total_affected"] == 2

    def test_create_snapshot(self):
        graph = KnowledgeGraph(name="Test")
        graph.add_node(KnowledgeNode(node_type="requirement", name="R1"))
        snapshot = graph.create_snapshot()
        assert snapshot["node_count"] == 1


class TestKnowledgeNode:
    def test_create_requirement_node(self):
        node = RequirementNode(name="Wing Span", parameter_name="span", parameter_value=2400, unit="mm")
        assert node.node_type == "requirement"
        assert node.parameter_name == "span"

    def test_create_design_node(self):
        node = DesignNode(name="Wing Design", model_type="parametric")
        assert node.node_type == "design"

    def test_update_properties(self):
        node = KnowledgeNode(name="Test")
        node.update_properties({"key": "value"})
        assert node.properties["key"] == "value"
        assert node.version == 2

    def test_add_remove_tag(self):
        node = KnowledgeNode(name="Test")
        node.add_tag("critical")
        assert "critical" in node.tags
        node.remove_tag("critical")
        assert "critical" not in node.tags

    def test_is_stale(self):
        node = KnowledgeNode(name="Test")
        assert not node.is_stale(90)


class TestKnowledgeLink:
    def test_create_link(self):
        link = KnowledgeLink(source_node_id="a", target_node_id="b", link_type="derives_from")
        assert link.link_type == "derives_from"

    def test_update_weight(self):
        link = KnowledgeLink(source_node_id="a", target_node_id="b", link_type="affects")
        link.update_weight(0.5)
        assert link.weight == 0.5
        with pytest.raises(ValueError):
            link.update_weight(1.5)

    def test_involves_node(self):
        link = KnowledgeLink(source_node_id="a", target_node_id="b", link_type="affects")
        assert link.involves_node("a")
        assert link.involves_node("b")
        assert not link.involves_node("c")

    def test_get_other_node(self):
        link = KnowledgeLink(source_node_id="a", target_node_id="b", link_type="affects")
        assert link.get_other_node("a") == "b"
        assert link.get_other_node("b") == "a"
        assert link.get_other_node("c") is None


class TestKnowledgeGraphService:
    def test_create_graph(self):
        svc = KnowledgeGraphService()
        graph = svc.create_graph("Test")
        assert graph.name == "Test"

    def test_create_node(self):
        svc = KnowledgeGraphService()
        graph = svc.create_graph("Test")
        node = svc.create_node(graph.graph_id, node_type="requirement", name="R1")
        assert node.node_type == "requirement"
        assert node.name == "R1"

    def test_create_node_invalid_type_raises(self):
        svc = KnowledgeGraphService()
        graph = svc.create_graph("Test")
        with pytest.raises(ValueError):
            svc.create_node(graph.graph_id, node_type="invalid", name="Test")

    def test_create_link(self):
        svc = KnowledgeGraphService()
        graph = svc.create_graph("Test")
        n1 = svc.create_node(graph.graph_id, node_type="requirement", name="R1")
        n2 = svc.create_node(graph.graph_id, node_type="design", name="D1")
        link = svc.create_link(graph.graph_id, n1.node_id, n2.node_id, "derives_from")
        assert link.link_type == "derives_from"

    def test_delete_node_cascades_links(self):
        svc = KnowledgeGraphService()
        graph = svc.create_graph("Test")
        n1 = svc.create_node(graph.graph_id, node_type="requirement", name="R1")
        n2 = svc.create_node(graph.graph_id, node_type="design", name="D1")
        svc.create_link(graph.graph_id, n1.node_id, n2.node_id, "derives_from")
        svc.delete_node(graph.graph_id, n1.node_id)
        g = svc.get_graph(graph.graph_id)
        assert g.node_count == 1
        assert g.link_count == 0

    def test_propagate_impact(self):
        svc = KnowledgeGraphService()
        graph = svc.create_graph("Test")
        n1 = svc.create_node(graph.graph_id, node_type="requirement", name="R1")
        n2 = svc.create_node(graph.graph_id, node_type="design", name="D1")
        svc.create_link(graph.graph_id, n1.node_id, n2.node_id, "derives_from", confidence=0.9)
        result = svc.propagate_impact(graph.graph_id, n1.node_id, depth=3)
        assert result.total_affected > 0

    def test_assess_quality(self):
        svc = KnowledgeGraphService()
        graph = svc.create_graph("Test")
        svc.create_node(graph.graph_id, node_type="requirement", name="R1")
        metrics = svc.assess_quality(graph.graph_id)
        assert isinstance(metrics, QualityMetrics)

    def test_detect_anomalies(self):
        svc = KnowledgeGraphService()
        graph = svc.create_graph("Test")
        svc.create_node(graph.graph_id, node_type="requirement", name="R1")
        anomalies = svc.detect_anomalies(graph.graph_id)
        assert isinstance(anomalies, list)

    def test_create_snapshot(self):
        svc = KnowledgeGraphService()
        graph = svc.create_graph("Test")
        svc.create_node(graph.graph_id, node_type="requirement", name="R1")
        snapshot = svc.create_snapshot(graph.graph_id)
        assert snapshot.node_count == 1
        assert len(snapshot.checksum) == 64


class TestImpactPropagationEngine:
    def test_propagate_impact(self):
        graph = KnowledgeGraph(name="Test")
        n1 = KnowledgeNode(node_type="requirement", name="R1")
        n2 = KnowledgeNode(node_type="design", name="D1")
        n3 = KnowledgeNode(node_type="structure", name="S1")
        graph.add_node(n1)
        graph.add_node(n2)
        graph.add_node(n3)
        graph.add_link(KnowledgeLink(source_node_id=n1.node_id, target_node_id=n2.node_id, link_type="derives_from", confidence=0.9))
        graph.add_link(KnowledgeLink(source_node_id=n2.node_id, target_node_id=n3.node_id, link_type="implements", confidence=0.8))
        engine = ImpactPropagationEngine()
        result = engine.propagate_impact(graph, n1.node_id, depth=3)
        assert len(result.affected_nodes) == 2
        assert result.affected_nodes[0]["confidence"] > result.affected_nodes[1]["confidence"]

    def test_propagate_impact_missing_source_raises(self):
        graph = KnowledgeGraph(name="Test")
        engine = ImpactPropagationEngine()
        with pytest.raises(ValueError):
            engine.propagate_impact(graph, "missing", depth=3)

    def test_compute_cascade_score(self):
        result = ImpactResult(source_node_id="a")
        result.add_affected_node("b", "design", 1, 0.8, ["derives_from"])
        result.add_affected_node("c", "structure", 2, 0.6, ["derives_from", "implements"])
        engine = ImpactPropagationEngine()
        score = engine.compute_cascade_score(result)
        assert score > 0

    def test_find_critical_paths(self):
        result = ImpactResult(source_node_id="a")
        result.add_affected_node("b", "design", 1, 0.9, ["derives_from"])
        result.add_affected_node("c", "structure", 2, 0.5, ["implements"])
        engine = ImpactPropagationEngine()
        critical = engine.find_critical_paths(result, threshold=0.7)
        assert len(critical) == 1
        assert critical[0]["node_id"] == "b"


class TestKnowledgeInferenceEngine:
    def test_transitive_inference(self):
        graph = KnowledgeGraph(name="Test")
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

    def test_rule_based_inference(self):
        graph = KnowledgeGraph(name="Test")
        n1 = KnowledgeNode(node_type="requirement", name="R1")
        n2 = KnowledgeNode(node_type="design", name="D1")
        graph.add_node(n1)
        graph.add_node(n2)
        engine = KnowledgeInferenceEngine()
        result = engine.infer_links(graph, [n1.node_id], reasoning_type="rule_based")
        assert len(result.inferred_links) >= 1


class TestKnowledgeQualityService:
    def test_assess_quality(self):
        graph = KnowledgeGraph(name="Test")
        graph.add_node(KnowledgeNode(node_type="requirement", name="R1"))
        graph.add_node(KnowledgeNode(node_type="design", name="D1"))
        n1 = graph.get_all_nodes()[0]
        n2 = graph.get_all_nodes()[1]
        graph.add_link(KnowledgeLink(source_node_id=n1.node_id, target_node_id=n2.node_id, link_type="derives_from"))
        svc = KnowledgeQualityService()
        metrics = svc.assess_quality(graph)
        assert metrics.connectivity == 1.0
        assert metrics.consistency == 1.0

    def test_detect_orphan_anomaly(self):
        graph = KnowledgeGraph(name="Test")
        graph.add_node(KnowledgeNode(node_type="requirement", name="R1"))
        svc = KnowledgeQualityService()
        anomalies = svc.detect_anomalies(graph)
        orphan_types = [a for a in anomalies if a.anomaly_type == "orphan"]
        assert len(orphan_types) == 1

    def test_resolve_anomaly(self):
        anomaly = AnomalyReport(anomaly_type="orphan", description="test")
        svc = KnowledgeQualityService()
        resolved = svc.resolve_anomaly(anomaly, "acknowledge")
        assert resolved.status == "acknowledged"


class TestKnowledgeSearchService:
    def test_keyword_search(self):
        graph = KnowledgeGraph(name="Test")
        graph.add_node(KnowledgeNode(node_type="requirement", name="Wing Span Requirement"))
        graph.add_node(KnowledgeNode(node_type="design", name="Fuselage Design"))
        svc = KnowledgeSearchService()
        results = svc.keyword_search(graph, "wing")
        assert len(results) == 1
        assert results[0][0].name == "Wing Span Requirement"

    def test_keyword_search_no_results(self):
        graph = KnowledgeGraph(name="Test")
        graph.add_node(KnowledgeNode(node_type="requirement", name="R1"))
        svc = KnowledgeSearchService()
        results = svc.keyword_search(graph, "nonexistent")
        assert len(results) == 0


class TestGraphSnapshotService:
    def test_create_snapshot(self):
        graph = KnowledgeGraph(name="Test")
        graph.add_node(KnowledgeNode(node_type="requirement", name="R1"))
        svc = GraphSnapshotService()
        snapshot = svc.create_snapshot(graph, name="test-snapshot")
        assert snapshot.name == "test-snapshot"
        assert snapshot.node_count == 1
        assert len(snapshot.checksum) == 64

    def test_compare_snapshots(self):
        graph = KnowledgeGraph(name="Test")
        graph.add_node(KnowledgeNode(node_type="requirement", name="R1"))
        svc = GraphSnapshotService()
        snap_a = svc.create_snapshot(graph, name="v1")
        graph.add_node(KnowledgeNode(node_type="design", name="D1"))
        snap_b = svc.create_snapshot(graph, name="v2")
        diff = svc.compare_snapshots(snap_a, snap_b)
        assert diff["nodes_added"] == 1


class TestQualityMetrics:
    def test_overall_score(self):
        metrics = QualityMetrics(completeness=1.0, consistency=1.0, timeliness=1.0, connectivity=1.0, coverage=1.0, freshness=1.0)
        assert metrics.overall_score == 1.0

    def test_zero_score(self):
        metrics = QualityMetrics()
        assert metrics.overall_score == 0.0


class TestAnomalyReport:
    def test_acknowledge(self):
        a = AnomalyReport(anomaly_type="orphan", description="test")
        a.acknowledge()
        assert a.status == "acknowledged"

    def test_resolve(self):
        a = AnomalyReport(anomaly_type="orphan", description="test")
        a.resolve("user1")
        assert a.status == "resolved"
        assert a.resolved_by == "user1"

    def test_dismiss(self):
        a = AnomalyReport(anomaly_type="orphan", description="test")
        a.dismiss()
        assert a.status == "dismissed"


class TestNodeType:
    def test_all_types(self):
        assert len(NodeType.values()) == 7
        assert NodeType.REQUIREMENT.value == "requirement"


class TestLinkType:
    def test_all_types(self):
        assert len(LinkType.values()) == 11
        assert LinkType.DERIVES_FROM.value == "derives_from"

    def test_cross_center_types(self):
        cross = LinkType.cross_center_types()
        assert len(cross) == 3