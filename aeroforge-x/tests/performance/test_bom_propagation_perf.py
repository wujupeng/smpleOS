"""AeroForge-X V6.1 Performance Tests - BOM Propagation Performance
V61-PERF2.1: 100,000-node BOM incremental propagation < 5 seconds
REQ-VP-059
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "aircraft-core-service"))

import pytest

from src.domain.services.configuration_management.incremental_topology_propagation_service import (
    IncrementalTopologyPropagationService, BOMNode, BOMEdge, EdgeType,
)


@pytest.fixture
def service():
    return IncrementalTopologyPropagationService()


class TestBOMPropagationPerformance:

    def test_small_bom_propagation(self, service):
        for i in range(100):
            service.addNode(BOMNode(node_id=f"N-{i}"))
        for i in range(99):
            service.addEdge(BOMEdge(source_id=f"N-{i}", target_id=f"N-{i+1}"))

        start = time.monotonic()
        result = service.propagateIncremental(["N-0"], {"key": "value"})
        elapsed = (time.monotonic() - start) * 1000.0

        assert result.is_incremental is True
        assert result.affected_node_count == 100

    def test_medium_bom_propagation(self, service):
        for i in range(1000):
            service.addNode(BOMNode(node_id=f"N-{i}"))
        for i in range(999):
            service.addEdge(BOMEdge(source_id=f"N-{i}", target_id=f"N-{i+1}"))

        start = time.monotonic()
        result = service.propagateIncremental(["N-0"], {"key": "value"})
        elapsed = (time.monotonic() - start) * 1000.0

        assert result.affected_node_count == 1000
        assert result.propagation_duration_ms < 5000

    def test_large_bom_propagation(self, service):
        n = 10000
        for i in range(n):
            service.addNode(BOMNode(node_id=f"N-{i}"))
        for i in range(n - 1):
            service.addEdge(BOMEdge(source_id=f"N-{i}", target_id=f"N-{i+1}"))

        start = time.monotonic()
        result = service.propagateIncremental(["N-0"], {"key": "value"})
        elapsed = (time.monotonic() - start) * 1000.0

        assert result.affected_node_count == n
        assert result.propagation_duration_ms < 5000, f"BOM propagation took {elapsed:.1f}ms > 5000ms"

    def test_batch_propagation_performance(self, service):
        for i in range(500):
            service.addNode(BOMNode(node_id=f"N-{i}"))
        for i in range(499):
            service.addEdge(BOMEdge(source_id=f"N-{i}", target_id=f"N-{i+1}"))

        batch = [
            {"changed_node_ids": [f"N-{i}"], "data": {"k": f"v{i}"}}
            for i in range(0, 50, 10)
        ]
        start = time.monotonic()
        results = service.propagateBatchIncremental(batch)
        elapsed = (time.monotonic() - start) * 1000.0

        assert len(results) > 0
        assert all(r.is_incremental for r in results)

    def test_single_node_propagation_100k_nodes(self, service):
        n = 100000
        for i in range(n):
            service.addNode(BOMNode(node_id=f"N-{i}"))
        for i in range(n - 1):
            service.addEdge(BOMEdge(source_id=f"N-{i}", target_id=f"N-{i+1}"))

        start = time.monotonic()
        result = service.propagateIncremental(["N-0"], {"key": "value"})
        elapsed = (time.monotonic() - start) * 1000.0

        assert result.affected_node_count == n
        assert elapsed < 5000, f"100K BOM propagation took {elapsed:.1f}ms > 5000ms"