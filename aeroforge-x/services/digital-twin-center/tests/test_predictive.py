import pytest

from services.digital_twin_center.src.domain.entities.predictive_models import (
    DegradationModel, DegradationModelType, AnomalySeverity,
)
from services.digital_twin_center.src.domain.services.predictive_maintenance_service import PredictiveMaintenanceService


class TestDegradationModel:
    def test_linear_predict_health(self) -> None:
        model = DegradationModel(
            model_type=DegradationModelType.LINEAR,
            current_health=0.8,
            degradation_rate=0.001,
        )
        health = model.predict_health_at(100)
        assert health == pytest.approx(0.7, abs=0.01)

    def test_linear_predict_rul(self) -> None:
        model = DegradationModel(
            model_type=DegradationModelType.LINEAR,
            current_health=0.8,
            degradation_rate=0.001,
            threshold=0.3,
        )
        rul = model.predict_rul()
        assert rul == pytest.approx(500.0, abs=1.0)

    def test_exponential_predict_rul(self) -> None:
        model = DegradationModel(
            model_type=DegradationModelType.EXPONENTIAL,
            current_health=0.8,
            degradation_rate=0.001,
            threshold=0.3,
        )
        rul = model.predict_rul()
        assert rul > 0

    def test_zero_degradation_rate(self) -> None:
        model = DegradationModel(
            degradation_rate=0,
            current_health=0.8,
        )
        rul = model.predict_rul()
        assert rul == float('inf')

    def test_below_threshold_rul(self) -> None:
        model = DegradationModel(
            current_health=0.2,
            threshold=0.3,
            degradation_rate=0.001,
        )
        rul = model.predict_rul()
        assert rul == 0


class TestPredictiveMaintenanceService:
    def test_build_degradation_model(self) -> None:
        service = PredictiveMaintenanceService()
        model = service.build_degradation_model(
            aircraft_sn="AC-001",
            component="wing_splice",
            model_type=DegradationModelType.LINEAR,
        )
        assert model.current_health > 0
        assert model.degradation_rate > 0

    def test_build_model_with_training_data(self) -> None:
        service = PredictiveMaintenanceService()
        training_data = [
            {"health": 1.0, "hours": 0},
            {"health": 0.95, "hours": 100},
            {"health": 0.85, "hours": 300},
            {"health": 0.75, "hours": 500},
        ]
        model = service.build_degradation_model(
            "AC-001", "engine", DegradationModelType.LINEAR, training_data,
        )
        assert model.training_samples == 4
        assert model.current_health == 0.75

    def test_predict_rul(self) -> None:
        service = PredictiveMaintenanceService()
        service.build_degradation_model("AC-001", "wing", DegradationModelType.LINEAR)
        prediction = service.predict_remaining_useful_life("AC-001", "wing")
        assert prediction is not None
        assert prediction.rul_hours > 0
        assert prediction.confidence_lower <= prediction.rul_hours
        assert prediction.confidence_upper >= prediction.rul_hours

    def test_predict_rul_no_model(self) -> None:
        service = PredictiveMaintenanceService()
        result = service.predict_remaining_useful_life("AC-999", "wing")
        assert result is None

    def test_predict_failure_probability(self) -> None:
        service = PredictiveMaintenanceService()
        service.build_degradation_model("AC-001", "engine", DegradationModelType.LINEAR)
        result = service.predict_failure_probability("AC-001", "engine")
        assert result is not None
        assert 0 <= result.probability_7d <= 1
        assert 0 <= result.probability_30d <= 1
        assert 0 <= result.probability_90d <= 1

    def test_failure_probability_exceeds_threshold(self) -> None:
        service = PredictiveMaintenanceService()
        training_data = [{"health": 0.4}, {"health": 0.3}]
        service.build_degradation_model("AC-001", "engine", training_data=training_data)
        result = service.predict_failure_probability("AC-001", "engine", threshold=0.05)
        assert result is not None
        assert result.probability_30d > 0

    def test_optimize_maintenance_schedule(self) -> None:
        service = PredictiveMaintenanceService()
        service.build_degradation_model("AC-001", "wing", DegradationModelType.LINEAR)
        service.build_degradation_model("AC-001", "engine", DegradationModelType.LINEAR)
        windows = service.optimize_maintenance_schedule("AC-001")
        assert len(windows) >= 1
        for w in windows:
            assert w.component != ""
            assert w.recommended_date != ""
            assert w.risk_if_deferred >= 0

    def test_detect_anomaly_normal(self) -> None:
        service = PredictiveMaintenanceService()
        detection = service.detect_anomaly_advanced(
            "AC-001", "engine",
            {"temperature": 80.0, "vibration": 2.5},
        )
        assert detection.is_anomaly is False
        assert detection.anomaly_score == 0

    def test_detect_anomaly_abnormal(self) -> None:
        service = PredictiveMaintenanceService()
        detection = service.detect_anomaly_advanced(
            "AC-001", "engine",
            {"temperature": 120.0, "vibration": 5.0},
        )
        assert detection.is_anomaly is True
        assert len(detection.contributing_sensors) > 0

    def test_detect_anomaly_severity(self) -> None:
        service = PredictiveMaintenanceService()
        detection = service.detect_anomaly_advanced(
            "AC-001", "engine",
            {"temperature": 200.0, "vibration": 10.0, "pressure": 50.0},
        )
        assert detection.severity in [AnomalySeverity.CRITICAL, AnomalySeverity.EMERGENCY]

    def test_get_anomalies(self) -> None:
        service = PredictiveMaintenanceService()
        service.detect_anomaly_advanced("AC-001", "engine", {"temperature": 150.0})
        service.detect_anomaly_advanced("AC-001", "wing", {"temperature": 80.0})
        anomalies = service.get_anomalies("AC-001")
        assert len(anomalies) >= 1

    def test_get_maintenance_windows(self) -> None:
        service = PredictiveMaintenanceService()
        service.build_degradation_model("AC-001", "engine")
        service.optimize_maintenance_schedule("AC-001")
        windows = service.get_maintenance_windows("AC-001")
        assert len(windows) >= 1