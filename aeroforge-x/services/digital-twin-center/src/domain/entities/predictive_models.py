from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from aeroforge_common.domain.base import DomainEvent


class DegradationModelType(str, Enum):
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    WIENER = "wiener"


class AnomalySeverity(str, Enum):
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class DegradationModel:
    model_type: DegradationModelType = DegradationModelType.LINEAR
    initial_health: float = 1.0
    degradation_rate: float = 0.001
    current_health: float = 1.0
    threshold: float = 0.3
    trained_at: str = ""
    training_samples: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_type": self.model_type.value,
            "initial_health": self.initial_health,
            "degradation_rate": self.degradation_rate,
            "current_health": round(self.current_health, 6),
            "threshold": self.threshold,
            "trained_at": self.trained_at,
            "training_samples": self.training_samples,
        }

    def predict_health_at(self, hours_ahead: float) -> float:
        if self.model_type == DegradationModelType.LINEAR:
            return max(0, self.current_health - self.degradation_rate * hours_ahead)
        elif self.model_type == DegradationModelType.EXPONENTIAL:
            return max(0, self.current_health * (1 - self.degradation_rate) ** hours_ahead)
        elif self.model_type == DegradationModelType.WIENER:
            import random
            drift = self.degradation_rate * hours_ahead
            return max(0, self.current_health - drift + random.gauss(0, 0.01 * hours_ahead ** 0.5))
        return self.current_health

    def predict_rul(self) -> float:
        if self.degradation_rate <= 0:
            return float('inf')
        if self.model_type == DegradationModelType.LINEAR:
            return max(0, (self.current_health - self.threshold) / self.degradation_rate)
        elif self.model_type == DegradationModelType.EXPONENTIAL:
            if self.current_health <= self.threshold:
                return 0
            import math
            return math.log(self.current_health / self.threshold) / max(self.degradation_rate, 1e-9)
        elif self.model_type == DegradationModelType.WIENER:
            return max(0, (self.current_health - self.threshold) / max(self.degradation_rate, 1e-9))
        return 0


@dataclass
class RULPrediction:
    aircraft_sn: str = ""
    component: str = ""
    rul_hours: float = 0.0
    confidence_lower: float = 0.0
    confidence_upper: float = 0.0
    confidence_level: float = 0.95
    current_health: float = 1.0
    predicted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "aircraft_sn": self.aircraft_sn,
            "component": self.component,
            "rul_hours": round(self.rul_hours, 2),
            "confidence_lower": round(self.confidence_lower, 2),
            "confidence_upper": round(self.confidence_upper, 2),
            "confidence_level": self.confidence_level,
            "current_health": round(self.current_health, 6),
            "predicted_at": self.predicted_at,
        }


@dataclass
class FailureProbability:
    aircraft_sn: str = ""
    component: str = ""
    probability_7d: float = 0.0
    probability_30d: float = 0.0
    probability_90d: float = 0.0
    threshold: float = 0.1
    exceeds_threshold: bool = False
    severity: AnomalySeverity = AnomalySeverity.WARNING
    calculated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "aircraft_sn": self.aircraft_sn,
            "component": self.component,
            "probability_7d": round(self.probability_7d, 4),
            "probability_30d": round(self.probability_30d, 4),
            "probability_90d": round(self.probability_90d, 4),
            "threshold": self.threshold,
            "exceeds_threshold": self.exceeds_threshold,
            "severity": self.severity.value,
            "calculated_at": self.calculated_at,
        }


@dataclass
class MaintenanceWindow:
    window_id: str = field(default_factory=lambda: str(uuid4()))
    component: str = ""
    recommended_date: str = ""
    earliest_date: str = ""
    latest_date: str = ""
    estimated_duration_hours: float = 8.0
    risk_if_deferred: float = 0.0
    cost_estimate: float = 0.0
    priority: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "window_id": self.window_id,
            "component": self.component,
            "recommended_date": self.recommended_date,
            "earliest_date": self.earliest_date,
            "latest_date": self.latest_date,
            "estimated_duration_hours": self.estimated_duration_hours,
            "risk_if_deferred": round(self.risk_if_deferred, 4),
            "cost_estimate": self.cost_estimate,
            "priority": self.priority,
        }


@dataclass
class AnomalyDetection:
    aircraft_sn: str = ""
    component: str = ""
    is_anomaly: bool = False
    severity: AnomalySeverity = AnomalySeverity.WARNING
    anomaly_score: float = 0.0
    contributing_sensors: list[str] = field(default_factory=list)
    description: str = ""
    detected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "aircraft_sn": self.aircraft_sn,
            "component": self.component,
            "is_anomaly": self.is_anomaly,
            "severity": self.severity.value,
            "anomaly_score": round(self.anomaly_score, 4),
            "contributing_sensors": self.contributing_sensors,
            "description": self.description,
            "detected_at": self.detected_at,
        }