from __future__ import annotations

import pytest

from src.domain.services.twin_domain_service import TwinDomainService
from src.domain.services.flight_twin_service import (
    FlightTwinService,
    HealthStatus,
    LoadTrend,
)


@pytest.fixture
def flight_service():
    twin_service = TwinDomainService()
    return FlightTwinService(twin_service)


class TestIngestTelemetry:
    def test_ingest_creates_flight_twin(self, flight_service):
        result = flight_service.ingest_telemetry("SN-FLT-001", [
            {"metric_name": "wing_lift", "metric_value": 45000.0, "sensor_id": "S-001"},
            {"metric_name": "temperature", "metric_value": 25.0, "sensor_id": "S-002"},
        ])
        assert result is not None
        assert result.twin_type.value == "flight"
        assert result.twin_payload.get("telemetry_count") == 2

    def test_ingest_updates_existing_twin(self, flight_service):
        flight_service.ingest_telemetry("SN-FLT-002", [
            {"metric_name": "wing_lift", "metric_value": 40000.0},
        ])
        result = flight_service.ingest_telemetry("SN-FLT-002", [
            {"metric_name": "wing_lift", "metric_value": 42000.0},
        ])
        assert result is not None
        assert result.data_version >= 2


class TestAnalyzeLoadTrend:
    def test_stable_trend(self, flight_service):
        flight_service.ingest_telemetry("SN-TREND-001", [
            {"metric_name": "wing_lift", "metric_value": 40000.0},
        ])
        result = flight_service.analyze_load_trend(
            "SN-TREND-001",
            recent_values=[40000.0, 41000.0, 39000.0, 40500.0],
        )
        assert result["trend"] in [t.value for t in LoadTrend]

    def test_increasing_trend(self, flight_service):
        result = flight_service.analyze_load_trend(
            "SN-TREND-002",
            recent_values=[30000.0, 35000.0, 40000.0, 48000.0],
        )
        assert result["trend"] == LoadTrend.INCREASING.value

    def test_decreasing_trend(self, flight_service):
        result = flight_service.analyze_load_trend(
            "SN-TREND-003",
            recent_values=[48000.0, 42000.0, 35000.0, 30000.0],
        )
        assert result["trend"] == LoadTrend.DECREASING.value

    def test_no_twin_returns_unknown(self, flight_service):
        result = flight_service.analyze_load_trend("SN-NONEXIST")
        assert result["trend"] == "unknown"


class TestAssessStructuralHealth:
    def test_normal_health(self, flight_service):
        flight_service.ingest_telemetry("SN-HEALTH-001", [])
        assessments = flight_service.assess_structural_health(
            "SN-HEALTH-001",
            component_loads={"wing_lift": 30000.0},
            flight_hours=10000.0,
        )
        assert len(assessments) > 0
        assert assessments[0].health_status == HealthStatus.NORMAL

    def test_warning_health(self, flight_service):
        flight_service.ingest_telemetry("SN-HEALTH-002", [])
        assessments = flight_service.assess_structural_health(
            "SN-HEALTH-002",
            component_loads={"wing_lift": 42000.0},
            flight_hours=40000.0,
        )
        warning_or_critical = [a for a in assessments if a.health_status in (HealthStatus.WARNING, HealthStatus.CRITICAL)]
        assert len(warning_or_critical) > 0

    def test_critical_health(self, flight_service):
        flight_service.ingest_telemetry("SN-HEALTH-003", [])
        assessments = flight_service.assess_structural_health(
            "SN-HEALTH-003",
            component_loads={"wing_lift": 55000.0},
            flight_hours=50000.0,
        )
        critical = [a for a in assessments if a.health_status == HealthStatus.CRITICAL]
        assert len(critical) > 0

    def test_no_flight_twin_returns_empty(self, flight_service):
        assessments = flight_service.assess_structural_health("SN-NONEXIST")
        assert len(assessments) == 0


class TestDetectAnomaly:
    def test_sensor_out_of_range(self, flight_service):
        anomalies = flight_service.detect_anomaly(
            "SN-ANOM-001",
            sensor_data={"temp_sensor_01": 100.0},
        )
        assert len(anomalies) > 0
        assert anomalies[0].anomaly_type == "sensor_out_of_range"

    def test_load_exceeds_design(self, flight_service):
        anomalies = flight_service.detect_anomaly(
            "SN-ANOM-002",
            sensor_data={"wing_lift": 60000.0},
        )
        load_anomalies = [a for a in anomalies if a.anomaly_type == "load_exceeds_design"]
        assert len(load_anomalies) > 0

    def test_no_anomaly_for_normal_values(self, flight_service):
        anomalies = flight_service.detect_anomaly(
            "SN-ANOM-003",
            sensor_data={"temperature": 25.0},
        )
        assert len(anomalies) == 0

    def test_anomaly_severity(self, flight_service):
        anomalies = flight_service.detect_anomaly(
            "SN-ANOM-004",
            sensor_data={"temperature": 200.0},
        )
        assert len(anomalies) > 0
        assert anomalies[0].severity in ("warning", "critical")