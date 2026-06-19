from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any

from ..domain.entities.quality_prediction import PredictionType
from ..domain.services.quality_prediction_service import QualityPredictionService

router = APIRouter(prefix="/api/v1/mes/quality-predictions", tags=["quality-prediction"])
_service = QualityPredictionService()


class InputFeatureRequest(BaseModel):
    name: str
    value: float
    feature_type: str = "process_parameter"
    unit: str = ""


class PredictRequest(BaseModel):
    tenant_id: str
    project_id: str
    work_order_id: str
    prediction_type: str = "operation_quality"
    input_features: list[InputFeatureRequest]
    model_version: str = "1.0.0"


class BuildModelRequest(BaseModel):
    tenant_id: str
    project_id: str
    model_type: str = "xgboost"


class OptimizeProcessRequest(BaseModel):
    prediction_id: str
    constraints: dict[str, Any] | None = None


class VerifyRequest(BaseModel):
    actual_quality: str
    actual_defects: list[str] | None = None
    verified_by: str = ""


@router.post("/build-model")
async def build_quality_model(req: BuildModelRequest):
    result = _service.build_quality_model(
        tenant_id=req.tenant_id,
        project_id=req.project_id,
        model_type=req.model_type,
    )
    return {"data": result}


@router.post("/predict")
async def predict_quality(req: PredictRequest):
    from ..domain.entities.quality_prediction import InputFeature
    features = [
        InputFeature(name=f.name, value=f.value, feature_type=f.feature_type, unit=f.unit)
        for f in req.input_features
    ]
    try:
        pred_type = PredictionType(req.prediction_type)
    except ValueError:
        pred_type = PredictionType.OPERATION_QUALITY

    prediction = _service.predict_quality(
        tenant_id=req.tenant_id,
        project_id=req.project_id,
        work_order_id=req.work_order_id,
        prediction_type=pred_type,
        input_features=features,
        model_version=req.model_version,
    )
    return {"data": prediction.to_detail_dict()}


@router.get("/{prediction_id}")
async def get_prediction(prediction_id: str):
    prediction = _service.get_prediction(prediction_id)
    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found")
    return {"data": prediction.to_detail_dict()}


@router.get("/{prediction_id}/drivers")
async def get_quality_drivers(prediction_id: str):
    shap_values = _service.identify_quality_drivers(prediction_id)
    if shap_values is None:
        raise HTTPException(status_code=404, detail="Prediction not found")
    return {"data": [sv.to_dict() for sv in shap_values]}


@router.post("/{prediction_id}/detect-drift")
async def detect_quality_drift(prediction_id: str):
    record = _service.detect_quality_drift(prediction_id)
    if not record:
        raise HTTPException(status_code=404, detail="Prediction not found")
    return {"data": record.to_dict()}


@router.post("/optimize-process")
async def optimize_process(req: OptimizeProcessRequest):
    recommendations = _service.optimize_process_for_quality(
        prediction_id=req.prediction_id,
        constraints=req.constraints,
    )
    if not recommendations:
        raise HTTPException(status_code=404, detail="Prediction not found")
    return {"data": [r.to_dict() for r in recommendations]}


@router.post("/{prediction_id}/verify")
async def verify_prediction(prediction_id: str, req: VerifyRequest):
    prediction = _service.verify_prediction(
        prediction_id=prediction_id,
        actual_quality=req.actual_quality,
        actual_defects=req.actual_defects,
        verified_by=req.verified_by,
    )
    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found")
    return {"data": prediction.to_detail_dict()}