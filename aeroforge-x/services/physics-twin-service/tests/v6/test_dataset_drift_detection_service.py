"""AeroForge-X V6.1 Unit Tests - DatasetDriftDetectionService
REQ-DG-005~009, REQ-VP-020
"""

import pytest

from src.domain.services.data_governance.dataset_drift_detection_service import (
    DatasetDriftDetectionService,
    DriftType,
    DriftDetectionResult,
    DriftHistoryEntry,
)


@pytest.fixture
def service():
    return DatasetDriftDetectionService()


class TestDetectFeatureDrift:

    def test_detect_no_drift(self, service):
        ref_data = {"CL": [0.5 + i * 0.001 for i in range(50)]}
        cur_data = {"CL": [0.5 + i * 0.001 for i in range(50)]}
        result = service.detectFeatureDrift("DS-001", "REF-001", ref_data, cur_data)
        assert isinstance(result, DriftDetectionResult)
        assert result.drift_type == DriftType.FEATURE
        assert result.is_drift_detected is False

    def test_detect_feature_drift(self, service):
        ref_data = {"CL": [0.5 + i * 0.001 for i in range(50)]}
        cur_data = {"CL": [0.8 + i * 0.001 for i in range(50)]}
        result = service.detectFeatureDrift("DS-001", "REF-001", ref_data, cur_data)
        assert result.is_drift_detected is True
        assert "CL" in result.affected_features

    def test_drift_recommended_action(self, service):
        ref_data = {"CL": [0.5 + i * 0.001 for i in range(50)]}
        cur_data = {"CL": [0.8 + i * 0.001 for i in range(50)]}
        result = service.detectFeatureDrift("DS-001", "REF-001", ref_data, cur_data)
        assert "Retrain" in result.recommended_action

    def test_drift_history_recorded(self, service):
        ref_data = {"CL": [0.5 + i * 0.001 for i in range(50)]}
        cur_data = {"CL": [0.8 + i * 0.001 for i in range(50)]}
        service.detectFeatureDrift("DS-001", "REF-001", ref_data, cur_data)
        history = service.getDriftHistory("DS-001")
        assert len(history) > 0

    def test_drift_alert_emitted(self, service):
        ref_data = {"CL": [0.5 + i * 0.001 for i in range(50)]}
        cur_data = {"CL": [0.8 + i * 0.001 for i in range(50)]}
        service.detectFeatureDrift("DS-001", "REF-001", ref_data, cur_data)
        alerts = service.getAlerts()
        assert len(alerts) > 0

    def test_no_alert_when_no_drift(self, service):
        ref_data = {"CL": [0.5 + i * 0.001 for i in range(50)]}
        cur_data = {"CL": [0.5 + i * 0.001 for i in range(50)]}
        service.detectFeatureDrift("DS-001", "REF-001", ref_data, cur_data)
        alerts = service.getAlerts()
        assert len(alerts) == 0


class TestDetectConceptDrift:

    def test_detect_no_concept_drift(self, service):
        baseline = [0.1 + i * 0.001 for i in range(50)]
        current = [0.1 + i * 0.001 for i in range(50)]
        result = service.detectConceptDrift("DS-001", "REF-001", baseline, current)
        assert result.drift_type == DriftType.CONCEPT
        assert result.is_drift_detected is False

    def test_detect_concept_drift(self, service):
        baseline = [0.1 + i * 0.001 for i in range(50)]
        current = [0.5 + i * 0.001 for i in range(50)]
        result = service.detectConceptDrift("DS-001", "REF-001", baseline, current)
        assert result.is_drift_detected is True
        assert result.concept_drift_magnitude > 0

    def test_concept_drift_empty_data(self, service):
        result = service.detectConceptDrift("DS-001", "REF-001", [], [])
        assert result.is_drift_detected is False


class TestComputePSI:

    def test_compute_psi_no_drift(self, service):
        ref_data = {"CL": [0.5 + i * 0.01 for i in range(100)]}
        cur_data = {"CL": [0.5 + i * 0.01 for i in range(100)]}
        result = service.computePSI("DS-001", "REF-001", ref_data, cur_data)
        assert result.psi_value < 0.25 or result.is_drift_detected is False

    def test_compute_psi_with_drift(self, service):
        ref_data = {"CL": [0.5 + i * 0.01 for i in range(100)]}
        cur_data = {"CL": [0.9 + i * 0.01 for i in range(100)]}
        result = service.computePSI("DS-001", "REF-001", ref_data, cur_data)
        assert isinstance(result, DriftDetectionResult)