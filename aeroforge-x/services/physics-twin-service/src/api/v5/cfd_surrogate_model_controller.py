from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.services.generative_design.cfd_surrogate_model_service import (
    CFDSurrogateModelService,
    SurrogateModelSpec,
    Architecture,
    QualityStatus,
    FlightCondition,
)

router = APIRouter(prefix="/api/v5/physics-twin/cfd-surrogate-models", tags=["CFD Surrogate Model v5"])

_service = CFDSurrogateModelService()


@router.post("")
async def train_surrogate_model(body: dict[str, Any]):
    architecture_str = body.get("architecture", "PINN")
    try:
        architecture = Architecture(architecture_str)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid architecture: {architecture_str}")

    model_id = body.get("model_id", f"CFD-SM-{architecture_str}-{hash(str(body)) % 10000:04d}")
    dataset_path = body.get("dataset_path", "")

    spec = SurrogateModelSpec(
        model_id=model_id,
        architecture=architecture,
        input_dimensions=body.get("input_dimensions", ["alpha", "beta", "mach", "reynolds"]),
        output_dimensions=body.get("output_dimensions", ["CL", "CD", "CM", "CY", "Cl", "Cn"]),
        training_dataset_ref=dataset_path,
    )

    result = _service.train_model(spec=spec, dataset_path=dataset_path)
    return {
        "model_id": result.model_id,
        "success": result.success,
        "r_squared": result.r_squared,
        "rmse": result.rmse,
        "training_duration_s": result.training_duration_s,
        "message": result.message,
    }


@router.post("/predict")
async def predict_aero_coefficients(body: dict[str, Any]):
    condition = FlightCondition(
        alpha=body.get("alpha", 0.0),
        beta=body.get("beta", 0.0),
        mach=body.get("mach", 0.0),
        reynolds=body.get("reynolds", 1e6),
        altitude=body.get("altitude", 0.0),
        dynamic_pressure=body.get("dynamic_pressure", 0.0),
    )

    prediction = _service.predict_aero_coefficients(condition=condition)
    return {
        "CL": prediction.CL,
        "CD": prediction.CD,
        "CM": prediction.CM,
        "CY": prediction.CY,
        "Cl": prediction.Cl,
        "Cn": prediction.Cn,
        "confidence": prediction.confidence,
        "is_fallback": prediction.is_fallback,
        "fallback_reason": prediction.fallback_reason,
    }


@router.post("/{model_id}/online-update")
async def online_update_model(model_id: str, body: dict[str, Any]):
    new_data_path = body.get("new_data_path", "")
    result = _service.online_update(model_id=model_id, new_data_path=new_data_path)
    return {
        "model_id": result.model_id,
        "success": result.success,
        "previous_r_squared": result.previous_r_squared,
        "new_r_squared": result.new_r_squared,
        "message": result.message,
    }


@router.get("/{model_id}/quality")
async def get_model_quality(model_id: str):
    metrics = _service.get_model_quality_metrics(model_id)
    if metrics is None:
        raise HTTPException(status_code=404, detail="Model not found")
    return {
        "model_id": metrics.model_id,
        "r_squared": metrics.r_squared,
        "rmse": metrics.rmse,
        "prediction_interval_coverage": metrics.prediction_interval_coverage,
        "test_set_size": metrics.test_set_size,
        "last_validated_at": metrics.last_validated_at,
    }


@router.put("/{model_id}/activate")
async def activate_model(model_id: str):
    result = _service.switch_model(model_id=model_id)
    return {
        "previous_model_id": result.previous_model_id,
        "new_model_id": result.new_model_id,
        "success": result.success,
    }


@router.post("/{model_id}/hot-swap")
async def hot_swap_model(model_id: str, body: dict[str, Any]):
    new_model_path = body.get("new_model_path", "")
    result = _service.hot_swap_model(model_id=model_id, new_model_path=new_model_path)
    return {
        "model_id": result.model_id,
        "success": result.success,
        "previous_weights_ref": result.previous_weights_ref,
        "new_weights_ref": result.new_weights_ref,
    }