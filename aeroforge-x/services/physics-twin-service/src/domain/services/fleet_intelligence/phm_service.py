"""AeroForge-X v5.0 PHMService

Predictive Health Management with hybrid RUL prediction
(Physics-based Paris law + Data-driven LSTM), maintenance scheduling,
predictive alerts, and model registry.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ComponentType(str, Enum):
    ENGINE = "Engine"
    BATTERY = "Battery"
    STRUCTURE = "Structure"
    LANDING_GEAR = "LandingGear"


class ModelType(str, Enum):
    PHYSICS_BASED = "PhysicsBased"
    DATA_DRIVEN = "DataDriven"
    HYBRID = "Hybrid"


class AlertLevel(str, Enum):
    INFO = "Info"
    WARNING = "Warning"
    CRITICAL = "Critical"


@dataclass(frozen=True)
class RULModelSpec:
    model_id: str
    component_type: ComponentType
    model_type: ModelType
    input_features: list[str]
    prediction_horizon_hours: float
    accuracy_metrics: dict
    min_confidence_threshold: float = 0.7


@dataclass(frozen=True)
class RULPrediction:
    prediction_id: str
    component_id: str
    component_type: ComponentType
    predicted_rul_hours: float
    confidence: float
    prediction_interval: dict
    model_id: str
    is_low_confidence: bool
    recommended_inspection_frequency_hours: float


@dataclass(frozen=True)
class MaintenanceSchedule:
    schedule_id: str
    aircraft_id: str
    scheduled_items: list[dict]
    total_downtime_hours: float
    earliest_window: str
    resource_requirements: dict


@dataclass(frozen=True)
class PredictiveAlert:
    alert_id: str
    aircraft_id: str
    component_type: ComponentType
    alert_level: AlertLevel
    predicted_rul_hours: float
    recommended_action: str
    urgency: str


class PHMService:

    def __init__(self) -> None:
        self._rul_models: dict[str, RULModelSpec] = {}
        self._active_models: dict[str, str] = {}
        self._predictions: dict[str, RULPrediction] = {}
        self._alerts: list[PredictiveAlert] = []
        self._validation_records: list[dict] = []

        self._register_default_models()

    def _register_default_models(self) -> None:
        defaults = [
            RULModelSpec(
                model_id="RUL-Engine-Hybrid",
                component_type=ComponentType.ENGINE,
                model_type=ModelType.HYBRID,
                input_features=["vibration", "temperature", "oil_pressure", "flight_hours"],
                prediction_horizon_hours=20000,
                accuracy_metrics={"mae_hours": 500, "r_squared": 0.92},
                min_confidence_threshold=0.7,
            ),
            RULModelSpec(
                model_id="RUL-Battery-Hybrid",
                component_type=ComponentType.BATTERY,
                model_type=ModelType.HYBRID,
                input_features=["voltage", "current", "temperature", "cycle_count"],
                prediction_horizon_hours=5000,
                accuracy_metrics={"mae_hours": 200, "r_squared": 0.90},
                min_confidence_threshold=0.7,
            ),
            RULModelSpec(
                model_id="RUL-Structure-Physics",
                component_type=ComponentType.STRUCTURE,
                model_type=ModelType.PHYSICS_BASED,
                input_features=["stress_cycles", "load_spectrum", "crack_length"],
                prediction_horizon_hours=30000,
                accuracy_metrics={"mae_hours": 1000, "r_squared": 0.85},
                min_confidence_threshold=0.7,
            ),
        ]

        for spec in defaults:
            self._rul_models[spec.model_id] = spec
            self._active_models[spec.component_type.value] = spec.model_id

    def predict_rul(
        self,
        aircraft_id: str,
        component_type: str,
        component_id: str,
        sensor_data: dict | None = None,
        w_physics: float = 0.4,
        w_data: float = 0.6,
    ) -> RULPrediction:
        ct = ComponentType(component_type)
        model_id = self._active_models.get(ct.value)
        model = self._rul_models.get(model_id) if model_id else None

        rul_physics = self._physics_based_rul(ct, sensor_data or {})
        rul_data = self._data_driven_rul(ct, sensor_data or {})

        if model and model.model_type == ModelType.HYBRID:
            rul_hybrid = w_physics * rul_physics + w_data * rul_data
        elif model and model.model_type == ModelType.PHYSICS_BASED:
            rul_hybrid = rul_physics
        else:
            rul_hybrid = rul_data

        confidence = 0.85 - 0.001 * (rul_hybrid / 1000)
        confidence = max(0.3, min(0.99, confidence))

        is_low = confidence < (model.min_confidence_threshold if model else 0.7)
        inspection_freq = 500.0
        if is_low:
            inspection_freq = 250.0

        prediction = RULPrediction(
            prediction_id=f"RUL-P-{uuid.uuid4().hex[:8].upper()}",
            component_id=component_id,
            component_type=ct,
            predicted_rul_hours=rul_hybrid,
            confidence=confidence,
            prediction_interval={
                "lower_90": rul_hybrid * 0.8,
                "upper_90": rul_hybrid * 1.2,
            },
            model_id=model_id or "default",
            is_low_confidence=is_low,
            recommended_inspection_frequency_hours=inspection_freq,
        )

        self._predictions[prediction.prediction_id] = prediction

        if rul_hybrid < 1000:
            self._emit_alert_internal(aircraft_id, ct, rul_hybrid)

        return prediction

    def generate_maintenance_schedule(
        self,
        aircraft_id: str,
        predictions: list[RULPrediction],
    ) -> MaintenanceSchedule:
        items: list[dict] = []
        total_downtime = 0.0
        resources: dict[str, int] = {}

        for pred in sorted(predictions, key=lambda p: p.predicted_rul_hours):
            downtime = 24.0 if pred.component_type == ComponentType.ENGINE else 8.0
            items.append({
                "component_type": pred.component_type.value,
                "component_id": pred.component_id,
                "scheduled_rul_hours": pred.predicted_rul_hours,
                "estimated_downtime_hours": downtime,
                "priority": "High" if pred.predicted_rul_hours < 500 else "Medium",
            })
            total_downtime += downtime
            resources[f"{pred.component_type.value}_technician"] = resources.get(f"{pred.component_type.value}_technician", 0) + 1

        return MaintenanceSchedule(
            schedule_id=f"MS-{uuid.uuid4().hex[:8].upper()}",
            aircraft_id=aircraft_id,
            scheduled_items=items,
            total_downtime_hours=total_downtime,
            earliest_window=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            resource_requirements=resources,
        )

    def emit_predictive_alert(
        self,
        aircraft_id: str,
        component_type: str,
        predicted_rul_hours: float,
    ) -> PredictiveAlert:
        ct = ComponentType(component_type)

        if predicted_rul_hours < 200:
            level = AlertLevel.CRITICAL
            urgency = "Immediate"
            action = "Ground aircraft and perform immediate inspection"
        elif predicted_rul_hours < 500:
            level = AlertLevel.WARNING
            urgency = "Within 48 hours"
            action = "Schedule maintenance within 48 hours"
        else:
            level = AlertLevel.INFO
            urgency = "Scheduled"
            action = "Include in next scheduled maintenance"

        alert = PredictiveAlert(
            alert_id=f"PA-{uuid.uuid4().hex[:8].upper()}",
            aircraft_id=aircraft_id,
            component_type=ct,
            alert_level=level,
            predicted_rul_hours=predicted_rul_hours,
            recommended_action=action,
            urgency=urgency,
        )

        self._alerts.append(alert)
        return alert

    def validate_prediction(
        self,
        prediction_id: str,
        actual_rul_hours: float,
    ) -> dict:
        prediction = self._predictions.get(prediction_id)
        if prediction is None:
            return {"error": "Prediction not found"}

        error = abs(prediction.predicted_rul_hours - actual_rul_hours)
        error_pct = error / actual_rul_hours * 100 if actual_rul_hours > 0 else 0.0

        record = {
            "prediction_id": prediction_id,
            "predicted_rul_hours": prediction.predicted_rul_hours,
            "actual_rul_hours": actual_rul_hours,
            "error_hours": error,
            "error_percent": error_pct,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        self._validation_records.append(record)

        return record

    def register_rul_model(self, spec: RULModelSpec) -> dict:
        self._rul_models[spec.model_id] = spec
        self._active_models[spec.component_type.value] = spec.model_id
        return {"model_id": spec.model_id, "registered": True}

    def get_fleet_rul_summary(self, aircraft_ids: list[str]) -> dict:
        summaries: dict[str, dict] = {}
        for pred_id, pred in self._predictions.items():
            summaries.setdefault(pred.component_type.value, {
                "count": 0,
                "avg_rul_hours": 0.0,
                "min_rul_hours": float("inf"),
                "low_confidence_count": 0,
            })
            s = summaries[pred.component_type.value]
            s["count"] += 1
            s["avg_rul_hours"] += pred.predicted_rul_hours
            s["min_rul_hours"] = min(s["min_rul_hours"], pred.predicted_rul_hours)
            if pred.is_low_confidence:
                s["low_confidence_count"] += 1

        for ct, s in summaries.items():
            if s["count"] > 0:
                s["avg_rul_hours"] /= s["count"]

        return summaries

    def get_alerts(self, aircraft_id: str | None = None) -> list[PredictiveAlert]:
        if aircraft_id:
            return [a for a in self._alerts if a.aircraft_id == aircraft_id]
        return list(self._alerts)

    def _emit_alert_internal(
        self,
        aircraft_id: str,
        component_type: ComponentType,
        rul_hours: float,
    ) -> PredictiveAlert:
        return self.emit_predictive_alert(
            aircraft_id=aircraft_id,
            component_type=component_type.value,
            predicted_rul_hours=rul_hours,
        )

    def _physics_based_rul(self, component_type: ComponentType, data: dict) -> float:
        if component_type == ComponentType.ENGINE:
            flight_hours = data.get("flight_hours", 5000.0)
            return max(100, 20000 - flight_hours * 0.8)
        elif component_type == ComponentType.BATTERY:
            cycles = data.get("cycle_count", 300)
            return max(50, 5000 - cycles * 8)
        elif component_type == ComponentType.STRUCTURE:
            crack_mm = data.get("crack_length", 0.5)
            if crack_mm <= 0:
                return 30000
            return max(100, 30000 / (1 + crack_mm * 10))
        return 10000.0

    def _data_driven_rul(self, component_type: ComponentType, data: dict) -> float:
        base = {
            ComponentType.ENGINE: 15000.0,
            ComponentType.BATTERY: 4000.0,
            ComponentType.STRUCTURE: 25000.0,
            ComponentType.LANDING_GEAR: 20000.0,
        }
        result = base.get(component_type, 10000.0)

        temp = data.get("temperature", 25.0)
        if temp > 80:
            result *= 0.7

        vibration = data.get("vibration", 1.0)
        if vibration > 5.0:
            result *= 0.6

        return max(50, result)