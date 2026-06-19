from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.services.manufacturing.process_plan_generator_service import (
    ProcessPlanGeneratorService,
)

router = APIRouter(prefix="/api/v5/aircraft-core/process-plans", tags=["Process Plan v5"])

_service = ProcessPlanGeneratorService()


@router.post("")
async def generate_process_plan(body: dict[str, Any]):
    mbom_id = body.get("mbom_id", "")
    bom_nodes = body.get("bom_nodes", [])
    plan = _service.generate_process_plan(mbom_id=mbom_id, bom_nodes=bom_nodes)
    return plan.to_dict()


@router.post("/{plan_id}/validate")
async def validate_process_plan(plan_id: str):
    result = _service.validate_process_plan(plan_id=plan_id)
    return {
        "is_valid": result.is_valid,
        "violations": result.violations,
        "warnings": result.warnings,
    }


@router.post("/{plan_id}/optimize")
async def optimize_process_plan(plan_id: str):
    try:
        plan = _service.optimize_process_plan(plan_id=plan_id)
        return plan.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))