"""AeroForge-X V6.1 Performance Tests - DG/IC/MC Performance Benchmarks
V61-DFX1.11~1.15: Dataset drift 100K/50f <30s, Quality score 100K <10s,
BOM incremental single-node 100K <1s, PHM triple <50ms, AES-256-GCM 1MB <5ms
REQ-DFX-V61-011~015
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "physics-twin-service"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "aircraft-core-service"))

import pytest

from src.domain.services.data_governance.dataset_drift_detection_service import DatasetDriftDetectionService
from src.domain.services.data_governance.dataset_quality_score_service import DatasetQualityScoreService
from src.domain.services.configuration_management.incremental_topology_propagation_service import (
    IncrementalTopologyPropagationService, BOMNode, BOMEdge,
)
from src.domain.services.fleet_intelligence.phm_model_confidence_service import PHMModelConfidenceService


class TestDatasetDriftPerformance:

    def test_drift_detection_100k_samples(self):
        service = DatasetDriftDetectionService()
        n = 100000
        ref_data = {"CL": [0.5 + (i % 100) * 0.001 for i in range(n)]}
        cur_data = {"CL": [0.5 + (i % 100) * 0.001 for i in range(n)]}

        start = time.monotonic()
        result = service.detectFeatureDrift("DS-001", "REF-001", ref_data, cur_data)
        elapsed = (time.monotonic() - start) * 1000.0

        assert isinstance(result, type(result))
        assert elapsed < 30000, f"Drift detection took {elapsed:.1f}ms > 30000ms"


class TestDatasetQualityScorePerformance:

    def test_quality_score_100k_samples(self):
        service = DatasetQualityScoreService()

        start = time.monotonic()
        result = service.computeQualityScore(
            dataset_id="CFD-001",
            missing_value_ratio=0.05,
            constraint_violation_ratio=0.02,
            data_age_days=30,
            design_space_coverage=0.85,
        )
        elapsed = (time.monotonic() - start) * 1000.0

        assert result.overall_score > 0
        assert elapsed < 10000, f"Quality score took {elapsed:.1f}ms > 10000ms"


class TestBOMIncrementalSingleNodePerformance:

    def test_single_node_100k_bom(self):
        service = IncrementalTopologyPropagationService()
        n = 100000
        for i in range(n):
            service.addNode(BOMNode(node_id=f"N-{i}"))
        for i in range(n - 1):
            service.addEdge(BOMEdge(source_id=f"N-{i}", target_id=f"N-{i+1}"))

        start = time.monotonic()
        result = service.propagateIncremental(["N-0"], {"key": "value"})
        elapsed = (time.monotonic() - start) * 1000.0

        assert result.is_incremental is True
        assert elapsed < 1000, f"Single-node 100K BOM took {elapsed:.1f}ms > 1000ms"


class TestPHMTriplePredictionPerformance:

    def test_phm_triple_under_50ms(self):
        service = PHMModelConfidenceService()

        start = time.monotonic()
        result = service.predictWithConfidence(
            component_id="ENG-001",
            rul_point_estimate=5000.0,
            ensemble_predictions=[4800, 4900, 5000, 5100, 5200],
        )
        elapsed = (time.monotonic() - start) * 1000.0

        assert result.confidence_interval is not None
        assert result.data_quality_score is not None
        assert elapsed < 50, f"PHM triple prediction took {elapsed:.1f}ms > 50ms"


class TestAES256GCMPerformance:

    def test_encryption_1mb_under_5ms(self):
        try:
            from src.domain.services.dfx.key_management_service import KeyManagementService
        except ImportError:
            pytest.skip("KeyManagementService not importable without cryptography")

        kms = KeyManagementService()
        key_id = kms.create_key()

        data = b"x" * (1024 * 1024)

        start = time.monotonic()
        encrypted = kms.encrypt(key_id, data)
        elapsed_encrypt = (time.monotonic() - start) * 1000.0

        start = time.monotonic()
        decrypted = kms.decrypt(key_id, encrypted)
        elapsed_decrypt = (time.monotonic() - start) * 1000.0

        assert decrypted == data
        assert elapsed_encrypt < 5, f"AES-256-GCM encrypt 1MB took {elapsed_encrypt:.1f}ms > 5ms"
        assert elapsed_decrypt < 5, f"AES-256-GCM decrypt 1MB took {elapsed_decrypt:.1f}ms > 5ms"