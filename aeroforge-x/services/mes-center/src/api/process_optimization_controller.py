from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

from ..domain.entities.process_optimization import OptimizationType
from ..domain.services.process_optimization_service import ProcessOptimizationService

router = APIRouter(prefix="/api/v1/mes/process-optimizations", tags=["process-optimization"])
_service = ProcessOptimizationService()


class AnalyzeBottleneckRequest(BaseModel):
    tenant_id: str
    project_id: str
    process_route_id: str


class OptimizeRequest(BaseModel):
    optimization_id: str
    optimization_type: str = "quality"


class SimulateRequest(BaseModel):
    optimization_id: str


class ValidateRequest(BaseModel):
    optimization_id: str
    sample_size: int = 30


class DeployRequest(BaseModel):
    optimization_id: str


@router.post("/analyze-bottleneck")
async def analyze_bottleneck(req: AnalyzeBottleneckRequest):
    result = _service.analyze_process_bottleneck(
        tenant_id=req.tenant_id,
        project_id=req.project_id,
        process_route_id=req.process_route_id,
    )
    return {"data": result.to_detail_dict()}


@router.post("/optimize")
async def optimize_process(req: OptimizeRequest):
    try:
        opt_type = OptimizationType(req.optimization_type)
    except ValueError:
        opt_type = OptimizationType.QUALITY

    result = _service.optimize_process_parameters(
        optimization_id=req.optimization_id,
        optimization_type=opt_type,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Optimization not found")
    return {"data": result.to_detail_dict()}


@router.post("/{optimization_id}/simulate")
async def simulate_change(optimization_id: str):
    result = _service.simulate_process_change(optimization_id)
    if not result:
        raise HTTPException(status_code=404, detail="Optimization not found")
    return {"data": result.to_detail_dict()}


@router.post("/{optimization_id}/validate")
async def validate_optimization(optimization_id: str, req: ValidateRequest):
    result = _service.validate_process_optimization(
        optimization_id=req.optimization_id,
        sample_size=req.sample_size,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Optimization not found")
    return {"data": result.to_detail_dict()}


@router.post("/{optimization_id}/deploy")
async def deploy_optimization(optimization_id: str):
    result = _service.deploy_optimized_process(optimization_id)
    if not result:
        raise HTTPException(status_code=400, detail="Optimization not found or not validated")
    return {"data": result.to_detail_dict()}


@router.get("/{optimization_id}")
async def get_optimization(optimization_id: str):
    result = _service.get_optimization(optimization_id)
    if not result:
        raise HTTPException(status_code=404, detail="Optimization not found")
    return {"data": result.to_detail_dict()}