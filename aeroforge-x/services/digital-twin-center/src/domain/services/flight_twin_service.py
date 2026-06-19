from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from aeroforge_common.domain.base import DomainEvent

from .digital_twin import DigitalTwin, SyncStatus, TwinType
from .twin_domain_service import TwinDomainService

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


class LoadTrend(str, Enum):
    INCREASING = "increasing"
    STABLE = "stable"
    DECREASING = "decreasing"


@dataclass
class AnomalyEvent:
    anomaly_id: str
    aircraft_sn: str
    sensor_id: str
    metric_name: str
    actual_value: float
    expected_range: tuple[float, float]
    anomaly_type: str
    severity: str = "warning"
    detected_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "anomaly_id": self.anomaly_id,
            "aircraft_sn": self.aircraft_sn,
            "sensor_id": self.sensor_id,
            "metric_name": self.metric_name,
            "actual_value": self.actual_value,
            "expected_range": list(self.expected_range),
            "anomaly_type": self.anomaly_type,
            "severity": self.severity,
            "detected_at": self.detected_at,
        }


@dataclass
class StructuralHealthAssessment:
    component_id: str
    component_name: str
    design_load: float
    actual_load: float
    load_ratio: float
    fatigue_damage_cumulative: float
    health_status: HealthStatus
    remaining_life_estimate_fh: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "component_name": self.component_name,
            "design_load": self.design_load,
            "actual_load": self.actual_load,
            "load_ratio": round(self.load_ratio, 4),
            "fatigue_damage_cumulative": round(self.fatigue_damage_cumulative, 6),
            "health_status": self.health_status.value,
            "remaining_life_estimate_fh": round(self.remaining_life_estimate_fh, 1),
        }


DESIGN_LOAD_LIMITS: dict[str, float] = {
    "wing_lift": 50000.0,
    "wing_bending_moment": 120000.0,
    "fuselage_pressure": 8.6,
    "tail_lateral_load": 30000.0,
    "engine_thrust": 25000.0,
    "landing_gear_load": 80000.0,
}

SENSOR_NORMAL_RANGES: dict[str, tuple[float, float]] = {
    "temperature": (-55.0, 85.0),
    "vibration_frequency": (0.0, 2000.0),
    "pressure": (0.0, 120.0),
    "strain": (-5000.0, 5000.0),
    "acceleration": (-9.0, 9.0),
    "rpm": (0.0, 25000.0),
}

FATIGUE_LIFE_BASELINE_FH: dict[str, float] = {
    "wing": 60000.0,
    "fuselage": 80000.0,
    "tail": 70000.0,
    "landing_gear": 20000.0,
    "engine_mount": 30000.0,
}


class FlightTwinService:
    def __init__(self, twin_service: TwinDomainService) -> None:
        self._twin_service = twin_service
        self._anomaly_counter: int = 0
        self._health_assessments: dict[str, list[StructuralHealthAssessment]] = {}

    def ingest_telemetry(
        self,
        aircraft_sn: str,
        telemetry_data: list[dict[str, Any]],
    ) -> DigitalTwin | None:
        twins = self._twin_service.get_twin_by_aircraft_sn(aircraft_sn, TwinType.FLIGHT)
        if not twins:
            twin = self._twin_service.create_twin(
                aircraft_serial_number=aircraft_sn,
                twin_type=TwinType.FLIGHT,
                entity_id=aircraft_sn,
                entity_type="aircraft_flight_data",
            )
        else:
            twin = twins[0]

        latest_metrics: dict[str, Any] = {}
        for rec in telemetry_data:
            metric_name = rec.get("metric_name", "")
            metric_value = rec.get("metric_value", 0.0)
            latest_metrics[metric_name] = metric_value

        payload: dict[str, Any] = {
            "flight_loads": {k: v for k, v in latest_metrics.items() if "load" in k.lower() or "lift" in k.lower()},
            "inferred_dimensions": {},
            "latest_telemetry": latest_metrics,
            "telemetry_count": len(telemetry_data),
        }

        twin.sync("telemetry_ingest", payload)
        logger.info("Ingested %d telemetry records for %s", len(telemetry_data), aircraft_sn)
        return twin

    def analyze_load_trend(
        self,
        aircraft_sn: str,
        metric_name: str = "wing_lift",
        recent_values: list[float] | None = None,
    ) -> dict[str, Any]:
        twins = self._twin_service.get_twin_by_aircraft_sn(aircraft_sn, TwinType.FLIGHT)
        if not twins:
            return {"aircraft_sn": aircraft_sn, "trend": "unknown", "message": "No flight twin found"}

        twin = twins[0]
        loads = recent_values or twin.twin_payload.get("flight_loads", {})

        if isinstance(loads, dict):
            values = list(loads.values()) if loads else []
        elif isinstance(loads, list):
            values = loads
        else:
            values = []

        if len(values) < 2:
            return {
                "aircraft_sn": aircraft_sn,
                "metric_name": metric_name,
                "trend": LoadTrend.STABLE.value,
                "data_points": len(values),
            }

        first_half = sum(values[:len(values) // 2]) / max(len(values) // 2, 1)
        second_half = sum(values[len(values) // 2:]) / max(len(values) - len(values) // 2, 1)

        change_ratio = (second_half - first_half) / max(abs(first_half), 1e-9)

        if change_ratio > 0.05:
            trend = LoadTrend.INCREASING
        elif change_ratio < -0.05:
            trend = LoadTrend.DECREASING
        else:
            trend = LoadTrend.STABLE

        return {
            "aircraft_sn": aircraft_sn,
            "metric_name": metric_name,
            "trend": trend.value,
            "change_ratio": round(change_ratio, 4),
            "first_half_avg": round(first_half, 2),
            "second_half_avg": round(second_half, 2),
            "data_points": len(values),
        }

    def assess_structural_health(
        self,
        aircraft_sn: str,
        component_loads: dict[str, float] | None = None,
        flight_hours: float = 0.0,
    ) -> list[StructuralHealthAssessment]:
        twins = self._twin_service.get_twin_by_aircraft_sn(aircraft_sn, TwinType.FLIGHT)
        if not twins:
            return []

        twin = twins[0]
        flight_loads = component_loads or twin.twin_payload.get("flight_loads", {})

        assessments: list[StructuralHealthAssessment] = []

        for component_key, actual_load in flight_loads.items():
            if not isinstance(actual_load, (int, float)):
                continue

            design_load = DESIGN_LOAD_LIMITS.get(component_key, 0.0)
            if design_load == 0:
                continue

            load_ratio = actual_load / design_load

            baseline_life = FATIGUE_LIFE_BASELINE_FH.get(component_key.split("_")[0], 60000.0)
            fatigue_damage = min(flight_hours / baseline_life, 1.0) * load_ratio

            if load_ratio > 1.0 or fatigue_damage > 0.8:
                health = HealthStatus.CRITICAL
            elif load_ratio > 0.8 or fatigue_damage > 0.6:
                health = HealthStatus.WARNING
            else:
                health = HealthStatus.NORMAL

            remaining_life = max(0, baseline_life * (1 - fatigue_damage))

            assessment = StructuralHealthAssessment(
                component_id=component_key,
                component_name=component_key.replace("_", " ").title(),
                design_load=design_load,
                actual_load=actual_load,
                load_ratio=load_ratio,
                fatigue_damage_cumulative=fatigue_damage,
                health_status=health,
                remaining_life_estimate_fh=remaining_life,
            )
            assessments.append(assessment)

        self._health_assessments[aircraft_sn] = assessments

        critical = [a for a in assessments if a.health_status == HealthStatus.CRITICAL]
        if critical:
            twin.add_domain_event(DomainEvent(
                event_type="twin.structural_health_critical",
                aggregate_id=twin.id,
                payload={
                    "aircraft_sn": aircraft_sn,
                    "critical_components": [a.to_dict() for a in critical],
                },
            ))

        return assessments

    def detect_anomaly(
        self,
        aircraft_sn: str,
        sensor_data: dict[str, float],
    ) -> list[AnomalyEvent]:
        from datetime import datetime, timezone

        anomalies: list[AnomalyEvent] = []

        for sensor_id, value in sensor_data.items():
            metric_name = self._infer_metric_from_sensor(sensor_id)
            normal_range = SENSOR_NORMAL_RANGES.get(metric_name)

            if normal_range is None:
                continue

            low, high = normal_range
            if value < low or value > high:
                self._anomaly_counter += 1
                anomaly = AnomalyEvent(
                    anomaly_id=f"ANOM-{self._anomaly_counter:06d}",
                    aircraft_sn=aircraft_sn,
                    sensor_id=sensor_id,
                    metric_name=metric_name,
                    actual_value=value,
                    expected_range=(low, high),
                    anomaly_type="sensor_out_of_range",
                    severity="critical" if abs(value - (low + high) / 2) > (high - low) else "warning",
                    detected_at=datetime.now(timezone.utc).isoformat(),
                )
                anomalies.append(anomaly)

        load_anomalies = self._detect_load_anomalies(aircraft_sn, sensor_data)
        anomalies.extend(load_anomalies)

        if anomalies:
            twins = self._twin_service.get_twin_by_aircraft_sn(aircraft_sn, TwinType.FLIGHT)
            if twins:
                twin = twins[0]
                twin.twin_payload.setdefault("anomalies", [])
                twin.twin_payload["anomalies"].extend([a.to_dict() for a in anomalies])

        logger.info("Detected %d anomalies for %s", len(anomalies), aircraft_sn)
        return anomalies

    def _detect_load_anomalies(
        self,
        aircraft_sn: str,
        sensor_data: dict[str, float],
    ) -> list[AnomalyEvent]:
        from datetime import datetime, timezone

        anomalies: list[AnomalyEvent] = []

        for key, design_limit in DESIGN_LOAD_LIMITS.items():
            actual = sensor_data.get(key)
            if actual is not None and actual > design_limit:
                self._anomaly_counter += 1
                anomaly = AnomalyEvent(
                    anomaly_id=f"ANOM-{self._anomaly_counter:06d}",
                    aircraft_sn=aircraft_sn,
                    sensor_id=key,
                    metric_name=key,
                    actual_value=actual,
                    expected_range=(0.0, design_limit),
                    anomaly_type="load_exceeds_design",
                    severity="critical",
                    detected_at=datetime.now(timezone.utc).isoformat(),
                )
                anomalies.append(anomaly)

        return anomalies

    def _infer_metric_from_sensor(self, sensor_id: str) -> str:
        sid = sensor_id.lower()
        if "temp" in sid or "therm" in sid:
            return "temperature"
        if "vibr" in sid or "accel" in sid:
            return "vibration_frequency"
        if "press" in sid:
            return "pressure"
        if "strain" in sid:
            return "strain"
        if "rpm" in sid or "speed" in sid:
            return "rpm"
        return "unknown"

    def get_health_assessment(self, aircraft_sn: str) -> list[dict[str, Any]]:
        assessments = self._health_assessments.get(aircraft_sn, [])
        return [a.to_dict() for a in assessments]