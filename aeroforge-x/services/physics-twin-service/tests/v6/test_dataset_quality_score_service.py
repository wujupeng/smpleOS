"""AeroForge-X V6.1 Unit Tests - DatasetQualityScoreService
REQ-DG-010~013, REQ-VP-020
"""

import pytest

from src.domain.services.data_governance.dataset_quality_score_service import (
    DatasetQualityScoreService,
    DatasetQualityAssessment,
    QUALITY_THRESHOLD,
)


@pytest.fixture
def service():
    return DatasetQualityScoreService()


class TestComputeQualityScore:

    def test_perfect_quality(self, service):
        result = service.computeQualityScore(
            dataset_id="CFD-001",
            missing_value_ratio=0.0,
            constraint_violation_ratio=0.0,
            data_age_days=0.0,
            design_space_coverage=1.0,
        )
        assert isinstance(result, DatasetQualityAssessment)
        assert result.overall_score == 100.0
        assert result.completeness_score == 100.0
        assert result.consistency_score == 100.0
        assert result.timeliness_score == 100.0
        assert result.representativeness_score == 100.0

    def test_poor_quality(self, service):
        result = service.computeQualityScore(
            dataset_id="CFD-002",
            missing_value_ratio=0.5,
            constraint_violation_ratio=0.3,
            data_age_days=500,
            max_acceptable_age_days=365,
            design_space_coverage=0.3,
        )
        assert result.overall_score < QUALITY_THRESHOLD
        assert result.completeness_score < 80
        assert result.consistency_score < 80

    def test_moderate_quality(self, service):
        result = service.computeQualityScore(
            dataset_id="CFD-003",
            missing_value_ratio=0.05,
            constraint_violation_ratio=0.02,
            data_age_days=30,
            max_acceptable_age_days=365,
            design_space_coverage=0.85,
        )
        assert result.overall_score >= QUALITY_THRESHOLD

    def test_improvement_recommendations(self, service):
        result = service.computeQualityScore(
            dataset_id="CFD-004",
            missing_value_ratio=0.3,
            constraint_violation_ratio=0.3,
            data_age_days=500,
            max_acceptable_age_days=365,
            design_space_coverage=0.3,
        )
        assert len(result.improvement_recommendations) > 0

    def test_no_recommendations_for_good_data(self, service):
        result = service.computeQualityScore(
            dataset_id="CFD-005",
            missing_value_ratio=0.0,
            constraint_violation_ratio=0.0,
            data_age_days=0,
            design_space_coverage=1.0,
        )
        assert result.improvement_recommendations == ""


class TestQualityAlerts:

    def test_alert_emitted_for_low_quality(self, service):
        service.computeQualityScore(
            dataset_id="CFD-LOW",
            missing_value_ratio=0.5,
            constraint_violation_ratio=0.5,
            data_age_days=500,
            design_space_coverage=0.2,
        )
        alerts = service.getAlerts()
        assert len(alerts) > 0
        assert alerts[0]["subject"] == "aeroforge.v6.dataset.quality.degraded"

    def test_no_alert_for_high_quality(self, service):
        service.computeQualityScore(
            dataset_id="CFD-HIGH",
            missing_value_ratio=0.0,
            constraint_violation_ratio=0.0,
            data_age_days=0,
            design_space_coverage=1.0,
        )
        alerts = service.getAlerts()
        assert len(alerts) == 0


class TestUQUncertaintyInflation:

    def test_no_inflation_above_threshold(self, service):
        result = service.inflateUQUncertainty(base_uncertainty=0.05, quality_score=80.0)
        assert result == 0.05

    def test_inflation_below_threshold(self, service):
        result = service.inflateUQUncertainty(base_uncertainty=0.05, quality_score=50.0)
        assert result > 0.05

    def test_inflation_factor_proportional(self, service):
        r1 = service.inflateUQUncertainty(0.05, 60.0)
        r2 = service.inflateUQUncertainty(0.05, 40.0)
        assert r2 > r1


class TestAssessmentHistory:

    def test_multiple_assessments(self, service):
        service.computeQualityScore("CFD-001", missing_value_ratio=0.1)
        service.computeQualityScore("CFD-001", missing_value_ratio=0.05)
        history = service.getAssessments("CFD-001")
        assert len(history) == 2

    def test_latest_assessment(self, service):
        service.computeQualityScore("CFD-001", missing_value_ratio=0.1)
        service.computeQualityScore("CFD-001", missing_value_ratio=0.0)
        latest = service.getLatestAssessment("CFD-001")
        assert latest.completeness_score == 100.0

    def test_latest_nonexistent_returns_none(self, service):
        result = service.getLatestAssessment("FAKE-DS")
        assert result is None