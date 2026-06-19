"""AeroForge-X V6.1 Unit Tests - PHMModelConfidenceService
REQ-MC-001~009, REQ-VP-020
"""

import pytest

from src.domain.services.fleet_intelligence.phm_model_confidence_service import (
    PHMModelConfidenceService,
    ConfidenceInterval,
    PHMDataQualityScore,
    RULPredictionWithConfidence,
    MaintenanceDecisionAudit,
    LowConfidenceReview,
    LOW_CONFIDENCE_DQ_THRESHOLD,
)


@pytest.fixture
def service():
    return PHMModelConfidenceService()


class TestPredictWithConfidence:

    def test_predict_with_ensemble(self, service):
        result = service.predictWithConfidence(
            component_id="ENG-001",
            rul_point_estimate=5000.0,
            ensemble_predictions=[4800, 4900, 5000, 5100, 5200],
        )
        assert isinstance(result, RULPredictionWithConfidence)
        assert result.prediction_id.startswith("PHM-")
        assert result.rul_point_estimate == 5000.0
        assert result.confidence_interval is not None
        assert result.confidence_interval.lower > 0
        assert result.confidence_interval.upper > result.confidence_interval.lower

    def test_predict_without_ensemble(self, service):
        result = service.predictWithConfidence(
            component_id="ENG-002",
            rul_point_estimate=3000.0,
        )
        assert result.confidence_interval is not None
        assert result.confidence_interval.method == "PointEstimateMargin"

    def test_predict_stores_result(self, service):
        result = service.predictWithConfidence("ENG-001", 5000.0)
        stored = service.getPrediction(result.prediction_id)
        assert stored is not None


class TestComputeConfidenceInterval:

    def test_ci_with_predictions(self, service):
        ci = service.computeConfidenceInterval(
            rul_point_estimate=5000.0,
            ensemble_predictions=[4800, 4900, 5000, 5100, 5200],
        )
        assert isinstance(ci, ConfidenceInterval)
        assert ci.method == "EnsembleVariance"
        assert ci.width() > 0

    def test_ci_without_predictions(self, service):
        ci = service.computeConfidenceInterval(5000.0, [])
        assert ci.method == "PointEstimateMargin"
        assert ci.width() > 0

    def test_ci_90_percent(self, service):
        ci = service.computeConfidenceInterval(5000.0, [4800, 4900, 5000, 5100, 5200], 0.90)
        assert ci.confidence_level == 0.90

    def test_ci_width(self, service):
        ci = ConfidenceInterval(lower=4800.0, upper=5200.0)
        assert ci.width() == 400.0


class TestComputeDataQualityScore:

    def test_perfect_quality(self, service):
        dq = service.computeDataQualityScore("PHM-001")
        assert isinstance(dq, PHMDataQualityScore)
        assert dq.overall_score == 100.0

    def test_poor_quality(self, service):
        dq = service.computeDataQualityScore(
            "PHM-002",
            sensor_completeness=50.0,
            calibration_currency=60.0,
            operating_condition_coverage=40.0,
            failure_data_representativeness=30.0,
        )
        assert dq.overall_score < LOW_CONFIDENCE_DQ_THRESHOLD

    def test_quality_weighting(self, service):
        dq = service.computeDataQualityScore(
            "PHM-003",
            sensor_completeness=100.0,
            calibration_currency=100.0,
            operating_condition_coverage=100.0,
            failure_data_representativeness=0.0,
        )
        assert dq.overall_score == 80.0


class TestLowConfidenceFlagging:

    def test_flag_low_confidence(self, service):
        result = service.predictWithConfidence(
            "ENG-001", 5000.0,
            sensor_completeness=30.0,
            calibration_currency=30.0,
            operating_condition_coverage=30.0,
            failure_data_representativeness=30.0,
        )
        review = service.flagLowConfidence(result.prediction_id)
        assert isinstance(review, LowConfidenceReview)
        assert review.confidence_width_pct > 0

    def test_no_flag_for_high_confidence(self, service):
        result = service.predictWithConfidence("ENG-001", 5000.0, [4990, 5000, 5010])
        review = service.flagLowConfidence(result.prediction_id)
        assert review is None

    def test_flag_nonexistent_returns_none(self, service):
        review = service.flagLowConfidence("FAKE-ID")
        assert review is None


class TestIntegrateDatasetQuality:

    def test_integrate_good_quality(self, service):
        result = service.predictWithConfidence("ENG-001", 5000.0)
        dq = service.integrateDatasetQuality(result.prediction_id, 90.0)
        assert dq is not None
        assert dq.overall_score >= LOW_CONFIDENCE_DQ_THRESHOLD

    def test_integrate_poor_quality_reduces_score(self, service):
        result = service.predictWithConfidence("ENG-001", 5000.0)
        dq = service.integrateDatasetQuality(result.prediction_id, 30.0)
        assert dq.overall_score < 100.0

    def test_integrate_nonexistent_returns_none(self, service):
        result = service.integrateDatasetQuality("FAKE-ID", 50.0)
        assert result is None


class TestMaintenanceDecisionAudit:

    def test_log_decision(self, service):
        result = service.predictWithConfidence("ENG-001", 5000.0)
        audit = service.logMaintenanceDecision(
            result.prediction_id,
            decision_threshold=1000.0,
            decision_outcome="ScheduleMaintenance",
            engineer_approval="eng-1",
        )
        assert isinstance(audit, MaintenanceDecisionAudit)
        assert audit.audit_id.startswith("MDA-")
        assert audit.decision_outcome == "ScheduleMaintenance"

    def test_query_audit_trail(self, service):
        r1 = service.predictWithConfidence("ENG-001", 5000.0)
        service.logMaintenanceDecision(r1.prediction_id, 1000.0, "Schedule")
        trail = service.queryDecisionAuditTrail("ENG-001")
        assert len(trail) == 1

    def test_log_nonexistent_prediction_raises(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.logMaintenanceDecision("FAKE-ID", 1000.0, "Schedule")