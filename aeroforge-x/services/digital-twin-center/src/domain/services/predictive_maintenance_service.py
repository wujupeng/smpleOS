from __future__ import annotations

import logging
import math
import random
from typing import Any

from aeroforge_common.domain.base import DomainEvent

from ..entities.predictive_models import (
    DegradationModel, DegradationModelType,
    RULPrediction, FailureProbability, AnomalySeverity,
    MaintenanceWindow, AnomalyDetection,
)

logger = logging.getLogger(__name__)


class PredictiveMaintenanceService:
    def __init__(self) -> None:
        self._models: dict[str, DegradationModel] = {}
        self._rul_predictions: dict[str, RULPrediction] = {}
        self._failure_probs: dict[str, FailureProbability] = {}
        self._maintenance_windows: dict[str, list[MaintenanceWindow]] = {}
        self._anomalies: list[AnomalyDetection] = []

    def build_degradation_model(
        self,
        aircraft_sn: str,
        component: str,
        model_type: DegradationModelType = DegradationModelType.LINEAR,
        training_data: list[dict[str, Any]] | None = None,
    ) -> DegradationModel:
        key = f"{aircraft_sn}:{component}"

        degradation_rate = 0.001
        initial_health = 1.0
        current_health = 0.85
        threshold = 0.3

        if training_data:
            health_values = [d.get("health", 1.0) for d in training_data]
            if len(health_values) >= 2:
                initial_health = health_values[0]
                current_health = health_values[-1]
                total_hours = len(health_values) * 100
                if model_type == DegradationModelType.LINEAR:
                    degradation_rate = (initial_health - current_health) / max(total_hours, 1)
                elif model_type == DegradationModelType.EXPONENTIAL:
                    if initial_health > 0 and current_health > 0:
                        degradation_rate = 1 - (current_health / initial_health) ** (1 / max(total_hours, 1))
                else:
                    degradation_rate = (initial_health - current_health) / max(total_hours, 1)

        model = DegradationModel(
            model_type=model_type,
            initial_health=initial_health,
            degradation_rate=degradation_rate,
            current_health=current_health,
            threshold=threshold,
            training_samples=len(training_data) if training_data else 0,
        )
        model.trained_at = datetime.now(timezone.utc).isoformat()

        self._models[key] = model

        logger.info("Built degradation model for %s: type=%s, rate=%.6f",
                     key, model_type.value, degradation_rate)
        return model

    def predict_remaining_useful_life(
        self,
        aircraft_sn: str,
        component: str,
    ) -> RULPrediction | None:
        key = f"{aircraft_sn}:{component}"
        model = self._models.get(key)
        if model is None:
            return None

        rul = model.predict_rul()

        lower = rul * 0.8
        upper = rul * 1.2

        prediction = RULPrediction(
            aircraft_sn=aircraft_sn,
            component=component,
            rul_hours=round(rul, 2),
            confidence_lower=round(lower, 2),
            confidence_upper=round(upper, 2),
            current_health=model.current_health,
        )

        self._rul_predictions[key] = prediction
        return prediction

    def predict_failure_probability(
        self,
        aircraft_sn: str,
        component: str,
        threshold: float = 0.1,
    ) -> FailureProbability | None:
        key = f"{aircraft_sn}:{component}"
        model = self._models.get(key)
        if model is None:
            return None

        health_7d = model.predict_health_at(7 * 24)
        health_30d = model.predict_health_at(30 * 24)
        health_90d = model.predict_health_at(90 * 24)

        prob_7d = max(0, 1 - health_7d / model.current_health) if model.current_health > 0 else 1.0
        prob_30d = max(0, 1 - health_30d / model.current_health) if model.current_health > 0 else 1.0
        prob_90d = max(0, 1 - health_90d / model.current_health) if model.current_health > 0 else 1.0

        prob_7d = min(1.0, prob_7d)
        prob_30d = min(1.0, prob_30d)
        prob_90d = min(1.0, prob_90d)

        max_prob = max(prob_7d, prob_30d, prob_90d)
        exceeds = max_prob >= threshold

        if max_prob >= 0.5:
            severity = AnomalySeverity.EMERGENCY
        elif max_prob >= 0.2:
            severity = AnomalySeverity.CRITICAL
        elif exceeds:
            severity = AnomalySeverity.WARNING
        else:
            severity = AnomalySeverity.WARNING

        result = FailureProbability(
            aircraft_sn=aircraft_sn,
            component=component,
            probability_7d=prob_7d,
            probability_30d=prob_30d,
            probability_90d=prob_90d,
            threshold=threshold,
            exceeds_threshold=exceeds,
            severity=severity,
        )

        self._failure_probs[key] = result

        if exceeds:
            logger.warning("Failure probability exceeds threshold: %s, severity=%s", key, severity.value)

        return result

    def optimize_maintenance_schedule(
        self,
        aircraft_sn: str,
        components: list[str] | None = None,
    ) -> list[MaintenanceWindow]:
        windows: list[MaintenanceWindow] = []

        if components is None:
            components = [k.split(":")[1] for k in self._models.keys() if k.startswith(f"{aircraft_sn}:")]

        for comp in components:
            key = f"{aircraft_sn}:{comp}"
            model = self._models.get(key)
            if model is None:
                continue

            rul = model.predict_rul()

            recommended_hours = max(0, rul * 0.7)
            earliest_hours = max(0, rul * 0.5)
            latest_hours = rul * 0.9

            risk = 0.0
            if rul < 100:
                risk = 0.8
            elif rul < 500:
                risk = 0.3
            else:
                risk = 0.05

            cost = 1000 + (1 - model.current_health) * 5000

            priority = 1
            if risk > 0.5:
                priority = 3
            elif risk > 0.2:
                priority = 2

            from datetime import datetime, timezone, timedelta
            recommended_date = (datetime.now(timezone.utc) + timedelta(hours=recommended_hours)).isoformat()
            earliest_date = (datetime.now(timezone.utc) + timedelta(hours=earliest_hours)).isoformat()
            latest_date = (datetime.now(timezone.utc) + timedelta(hours=latest_hours)).isoformat()

            windows.append(MaintenanceWindow(
                component=comp,
                recommended_date=recommended_date,
                earliest_date=earliest_date,
                latest_date=latest_date,
                estimated_duration_hours=8.0,
                risk_if_deferred=risk,
                cost_estimate=round(cost, 2),
                priority=priority,
            ))

        windows.sort(key=lambda w: (-w.priority, w.risk_if_deferred), reverse=False)
        windows.sort(key=lambda w: -w.priority)

        self._maintenance_windows[aircraft_sn] = windows
        return windows

    def detect_anomaly_advanced(
        self,
        aircraft_sn: str,
        component: str,
        sensor_data: dict[str, float],
    ) -> AnomalyDetection:
        key = f"{aircraft_sn}:{component}"
        model = self._models.get(key)

        anomaly_score = 0.0
        contributing_sensors: list[str] = []
        is_anomaly = False

        baseline = {
            "temperature": 80.0,
            "vibration": 2.5,
            "pressure": 101.3,
            "rpm": 3000.0,
            "current": 15.0,
            "strain": 0.002,
        }

        for sensor, value in sensor_data.items():
            base = baseline.get(sensor, value)
            if base > 0:
                deviation = abs(value - base) / base
                if deviation > 0.3:
                    anomaly_score += deviation
                    contributing_sensors.append(sensor)
                    is_anomaly = True

        if model and model.current_health < 0.5:
            anomaly_score += (1 - model.current_health)
            is_anomaly = True

        severity = AnomalySeverity.WARNING
        if anomaly_score > 1.5:
            severity = AnomalySeverity.EMERGENCY
        elif anomaly_score > 0.8:
            severity = AnomalySeverity.CRITICAL

        detection = AnomalyDetection(
            aircraft_sn=aircraft_sn,
            component=component,
            is_anomaly=is_anomaly,
            severity=severity,
            anomaly_score=round(anomaly_score, 4),
            contributing_sensors=contributing_sensors,
            description=f"异常检测: {', '.join(contributing_sensors)} 偏离基线" if contributing_sensors else "无异常",
        )

        if is_anomaly:
            self._anomalies.append(detection)

        return detection

    def get_model(self, aircraft_sn: str, component: str) -> DegradationModel | None:
        return self._models.get(f"{aircraft_sn}:{component}")

    def get_rul_prediction(self, aircraft_sn: str, component: str) -> RULPrediction | None:
        return self._rul_predictions.get(f"{aircraft_sn}:{component}")

    def get_failure_probability(self, aircraft_sn: str, component: str) -> FailureProbability | None:
        return self._failure_probs.get(f"{aircraft_sn}:{component}")

    def get_maintenance_windows(self, aircraft_sn: str) -> list[MaintenanceWindow]:
        return self._maintenance_windows.get(aircraft_sn, [])

    def get_anomalies(self, aircraft_sn: str | None = None) -> list[AnomalyDetection]:
        if aircraft_sn:
            return [a for a in self._anomalies if a.aircraft_sn == aircraft_sn]
        return list(self._anomalies)


from datetime import datetime, timezone, timedelta  # noqa: E402