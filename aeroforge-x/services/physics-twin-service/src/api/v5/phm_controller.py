from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.services.fleet_intelligence.phm_service import PHMService

router = APIRouter(prefix="/api/v5/physics-twin/phm", tags=["PHM v5"])

_service = PHMService()


@router.post("/rul-predictions")
async def predict_rul(body: dict[str, Any]):
    prediction = _service.predict_rul(
        aircraft_id=body.get("aircraft_id", ""),
        component_type=body.get("component_type", "Engine"),
        component_id=body.get("component_id", ""),
        sensor_data=body.get("sensor_data"),
        w_physics=body.get("w_physics", 0.4),
        w_data=body.get("w_data", 0.6),
    )
    return {
        "prediction_id": prediction.prediction_id,
        "component_id": prediction.component_id,
        "component_type": prediction.component_type.value,
        "predicted_rul_hours": prediction.predicted_rul_hours,
        "confidence": prediction.confidence,
        "prediction_interval": prediction.prediction_interval,
        "model_id": prediction.model_id,
        "is_low_confidence": prediction.is_low_confidence,
        "recommended_inspection_frequency_hours": prediction.recommended_inspection_frequency_hours,
    }


@router.post("/maintenance-schedules")
async def generate_maintenance_schedule(body: dict[str, Any]):
    from src.domain.services.fleet_intelligence.phm_service import RULPrediction, ComponentType
    predictions_data = body.get("predictions", [])
    predictions = [
        RULPrediction(
            prediction_id=p.get("prediction_id", ""),
            component_id=p.get("component_id", ""),
            component_type=ComponentType(p.get("component_type", "Engine")),
            predicted_rul_hours=p.get("predicted_rul_hours", 0),
            confidence=p.get("confidence", 0.5),
            prediction_interval=p.get("prediction_interval", {}),
            model_id=p.get("model_id", ""),
            is_low_confidence=p.get("is_low_confidence", False),
            recommended_inspection_frequency_hours=p.get("recommended_inspection_frequency_hours", 500),
        )
        for p in predictions_data
    ]
    schedule = _service.generate_maintenance_schedule(
        aircraft_id=body.get("aircraft_id", ""),
        predictions=predictions,
    )
    return {
        "schedule_id": schedule.schedule_id,
        "aircraft_id": schedule.aircraft_id,
        "scheduled_items": schedule.scheduled_items,
        "total_downtime_hours": schedule.total_downtime_hours,
        "earliest_window": schedule.earliest_window,
        "resource_requirements": schedule.resource_requirements,
    }


@router.get("/alerts")
async def get_alerts(aircraft_id: str | None = None):
    alerts = _service.get_alerts(aircraft_id=aircraft_id)
    return {
        "alerts": [
            {
                "alert_id": a.alert_id,
                "aircraft_id": a.aircraft_id,
                "component_type": a.component_type.value,
                "alert_level": a.alert_level.value,
                "predicted_rul_hours": a.predicted_rul_hours,
                "recommended_action": a.recommended_action,
                "urgency": a.urgency,
            }
            for a in alerts
        ],
    }


@router.post("/predictions/{prediction_id}/validate")
async def validate_prediction(prediction_id: str, body: dict[str, Any]):
    result = _service.validate_prediction(
        prediction_id=prediction_id,
        actual_rul_hours=body.get("actual_rul_hours", 0),
    )
    return result


@router.post("/rul-models")
async def register_rul_model(body: dict[str, Any]):
    from src.domain.services.fleet_intelligence.phm_service import (
        RULModelSpec, ComponentType, ModelType,
    )
    spec = RULModelSpec(
        model_id=body.get("model_id", ""),
        component_type=ComponentType(body.get("component_type", "Engine")),
        model_type=ModelType(body.get("model_type", "Hybrid")),
        input_features=body.get("input_features", []),
        prediction_horizon_hours=body.get("prediction_horizon_hours", 10000),
        accuracy_metrics=body.get("accuracy_metrics", {}),
        min_confidence_threshold=body.get("min_confidence_threshold", 0.7),
    )
    result = _service.register_rul_model(spec)
    return result


@router.post("/fleet-rul-summary")
async def get_fleet_rul_summary(body: dict[str, Any]):
    aircraft_ids = body.get("aircraft_ids", [])
    summary = _service.get_fleet_rul_summary(aircraft_ids)
    return summary