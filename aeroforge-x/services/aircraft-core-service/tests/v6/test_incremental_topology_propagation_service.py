"""AeroForge-X V6.1 Unit Tests - IncrementalTopologyPropagationService
REQ-IC-001~010, REQ-VP-020
"""

import pytest

from src.domain.services.configuration_management.incremental_topology_propagation_service import (
    IncrementalTopologyPropagationService,
    BOMNode,
    BOMEdge,
    EdgeType,
    AffectedSubtree,
    PropagationResult,
)


@pytest.fixture
def service():
    return IncrementalTopologyPropagationService()


@pytest.fixture
def simple_tree(service):
    service.addNode(BOMNode(node_id="A", config_view_type="Design"))
    service.addNode(BOMNode(node_id="B", config_view_type="Design"))
    service.addNode(BOMNode(node_id="C", config_view_type="Manufacturing"))
    service.addNode(BOMNode(node_id="D", config_view_type="Manufacturing"))
    service.addEdge(BOMEdge(source_id="A", target_id="B", edge_type=EdgeType.DERIVATION))
    service.addEdge(BOMEdge(source_id="A", target_id="C", edge_type=EdgeType.PROPAGATION))
    service.addEdge(BOMEdge(source_id="B", target_id="D", edge_type=EdgeType.PROPAGATION))
    return service


class TestAddNodeAndEdge:

    def test_add_node(self, service):
        service.addNode(BOMNode(node_id="N1"))
        assert service.getNodeCount() == 1

    def test_add_edge(self, service):
        service.addNode(BOMNode(node_id="N1"))
        service.addNode(BOMNode(node_id="N2"))
        service.addEdge(BOMEdge(source_id="N1", target_id="N2"))
        assert "N2" in service._adjacency["N1"]


class TestBuildDependencyGraph:

    def test_build_from_dict(self, service):
        bom_tree = {
            "nodes": [
                {"node_id": "A", "parent_ids": [], "config_view_type": "Design"},
                {"node_id": "B", "parent_ids": ["A"], "config_view_type": "Manufacturing"},
            ],
            "edges": [
                {"source_id": "A", "target_id": "B", "edge_type": "Derivation"},
            ],
        }
        service.buildDependencyGraph(bom_tree)
        assert service.getNodeCount() == 2
        assert "B" in service._adjacency.get("A", [])


class TestComputeTopologicalOrder:

    def test_simple_topo_order(self, simple_tree):
        subtree = simple_tree.computeTopologicalOrder(["A"])
        assert isinstance(subtree, AffectedSubtree)
        assert "A" in subtree.affected_nodes
        assert "B" in subtree.affected_nodes
        assert "C" in subtree.affected_nodes
        assert "D" in subtree.affected_nodes

    def test_partial_topo_order(self, simple_tree):
        subtree = simple_tree.computeTopologicalOrder(["B"])
        assert "B" in subtree.affected_nodes
        assert "D" in subtree.affected_nodes
        assert "A" not in subtree.affected_nodes

    def test_topo_order_respects_dependencies(self, simple_tree):
        subtree = simple_tree.computeTopologicalOrder(["A"])
        a_idx = subtree.topological_order.index("A")
        b_idx = subtree.topological_order.index("B")
        assert a_idx < b_idx


class TestPropagateIncremental:

    def test_incremental_propagation(self, simple_tree):
        result = simple_tree.propagateIncremental(["A"], {"key": "value"})
        assert isinstance(result, PropagationResult)
        assert result.is_incremental is True
        assert result.affected_node_count > 0
        assert result.propagation_duration_ms >= 0

    def test_propagation_updates_hash(self, simple_tree):
        simple_tree.propagateIncremental(["A"], {"key": "value"})
        node = simple_tree._nodes["A"]
        assert node.last_propagation_hash != ""

    def test_propagation_log_recorded(self, simple_tree):
        simple_tree.propagateIncremental(["A"], {"key": "value"})
        log = simple_tree.getPropagationLog()
        assert len(log) == 1


class TestBatchIncrementalPropagation:

    def test_batch_propagation(self, simple_tree):
        batch = [
            {"changed_node_ids": ["A"], "data": {"k1": "v1"}},
            {"changed_node_ids": ["B"], "data": {"k2": "v2"}},
        ]
        results = simple_tree.propagateBatchIncremental(batch)
        assert len(results) > 0
        assert all(r.is_incremental for r in results)

    def test_empty_batch(self, simple_tree):
        results = simple_tree.propagateBatchIncremental([])
        assert len(results) == 0