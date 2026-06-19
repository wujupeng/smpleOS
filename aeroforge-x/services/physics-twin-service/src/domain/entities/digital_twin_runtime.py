from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.domain.enums import FidelityLevel, HealthStatus
from src.domain.value_objects.active_model_ref import ActiveModelRef
from src.domain.value_objects.rul_prediction import RULPrediction
from src.domain.value_objects.health_indicator import HealthIndicator


class DigitalTwinRuntime(BaseModel):
    runtime_id: str = ""
    aircraft_object_id: str
    models: list[ActiveModelRef] = Field(default_factory=list)
    current_state: dict[str, Any] = Field(default_factory=dict)
    active_fidelity: FidelityLevel = FidelityLevel.Low
    health_indicators: list[HealthIndicator] = Field(default_factory=list)
    rul_predictions: list[RULPrediction] = Field(default_factory=list)
    data_lagged: bool = False
    last_sensor_timestamp: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def update_with_sensor_data(self, sensor_data: dict[str, Any]) -> dict[str, Any]:
        self.last_sensor_timestamp = datetime.utcnow()
        self.data_lagged = False
        self.current_state.update(sensor_data)
        self.updated_at = datetime.utcnow()
        return {"prediction_output": self.current_state}

    def switch_fidelity(self, level: FidelityLevel) -> None:
        self.active_fidelity = level
        self.updated_at = datetime.utcnow()

    def compute_health_indicator(self, component_id: str, predicted: float, measured: float) -> HealthIndicator:
        deviation = abs(predicted - measured) / max(abs(measured), 1e-10)
        score = max(0, min(100, int(100 * (1 - deviation))))

        if score >= 80:
            status = HealthStatus.Healthy
        elif score >= 60:
            status = HealthStatus.Warning
        else:
            status = HealthStatus.Critical

        indicator = HealthIndicator(
            component_id=component_id,
            score=score,
            status=status,
        )
        self.health_indicators.append(indicator)
        return indicator

    def mark_data_lagged(self) -> None:
        self.data_lagged = True