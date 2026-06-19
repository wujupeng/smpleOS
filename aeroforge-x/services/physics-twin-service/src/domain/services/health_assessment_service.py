from __future__ import annotations

from typing import Any

from src.domain.value_objects.health_indicator import HealthIndicator
from src.domain.value_objects.rul_prediction import RULPrediction
from src.domain.enums import HealthStatus


class HealthAssessmentService:

    @staticmethod
    def compute_health(predicted: float, measured: float, component_id: str) -> HealthIndicator:
        deviation = abs(predicted - measured) / max(abs(measured), 1e-10)
        score = max(0, min(100, int(100 * (1 - deviation))))

        if score >= 80:
            status = HealthStatus.Healthy
        elif score >= 60:
            status = HealthStatus.Warning
        else:
            status = HealthStatus.Critical

        return HealthIndicator(component_id=component_id, score=score, status=status)

    @staticmethod
    def predict_rul(component_id: str, degradation_rate: float, current_health: float,
                     threshold: float = 0.0, confidence: float = 0.9) -> RULPrediction:
        if degradation_rate <= 0:
            rul_value = float("inf")
        else:
            rul_value = (current_health - threshold) / degradation_rate

        lower = rul_value * (1 - (1 - confidence))
        upper = rul_value * (1 + (1 - confidence))

        return RULPrediction(
            component_id=component_id,
            rul_value=rul_value,
            confidence_interval=(lower, upper),
            confidence=confidence,
        )

    @staticmethod
    def diagnose_anomaly(predicted: float, measured: float, component_id: str,
                          threshold: float = 0.1) -> dict[str, Any]:
        deviation = abs(predicted - measured) / max(abs(measured), 1e-10)
        is_anomaly = deviation > threshold

        return {
            "component_id": component_id,
            "is_anomaly": is_anomaly,
            "deviation": deviation,
            "predicted": predicted,
            "measured": measured,
            "confidence": "low" if deviation < threshold * 2 else "high",
            "root_cause_hypothesis": "sensor_drift" if not is_anomaly else "component_degradation",
        }