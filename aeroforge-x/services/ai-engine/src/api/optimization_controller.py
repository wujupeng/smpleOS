from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from aeroforge_common.domain.responses import ApiResponse

from ..domain.entities.optimization_task import OptimizationAlgorithm, OptimizationType
from ..domain.services.multi_objective_optimizer import (
    MultiObjectiveOptimizer,
    BUILTIN_OBJECTIVES,
    BUILTIN_CONSTRAINTS,
    BUILTIN_DESIGN_VARIABLES,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ai", tags=["Optimization"])

_optimizer = MultiObjectiveOptimizer()


class CreateOptimizationRequest(BaseModel):
    project_id: str = Field(..., min_length=1)
    tenant_id: str = Field(default="default")
    objective_names: list[str] = Field(default_factory=lambda: ["minimize_weight", "maximize_lift_drag_ratio"])
    constraint_names: list[str] = Field(default_factory=lambda: ["safety_factor"])
    variable_names: list[str] = Field(default_factory=lambda: ["wing_span", "aspect_ratio"])
    algorithm: OptimizationAlgorithm = OptimizationAlgorithm.NSGA2
    max_iterations: int = Field(default=100, ge=1, le=1000)
    population_size: int = Field(default=50, ge=10, le=500)


class RunOptimizationRequest(BaseModel):
    task_id: str = Field(..., min_length=1)


@router.post("/optimization/create", response_model=ApiResponse[dict])
async def create_optimization_task(body: CreateOptimizationRequest):
    task = _optimizer.create_optimization_task(
        project_id=body.project_id,
        tenant_id=body.tenant_id,
        objective_names=body.objective_names,
        constraint_names=body.constraint_names,
        variable_names=body.variable_names,
        algorithm=body.algorithm,
        max_iterations=body.max_iterations,
        population_size=body.population_size,
    )
    return ApiResponse(data=task.to_dict())


@router.post("/optimization/run", response_model=ApiResponse[dict])
async def run_optimization(body: RunOptimizationRequest):
    task = _optimizer.run_optimization(body.task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Optimization task not found")
    return ApiResponse(data=task.to_dict())


@router.get("/optimization/tasks/{task_id}", response_model=ApiResponse[dict])
async def get_optimization_task(task_id: str):
    task = _optimizer.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Optimization task not found")
    return ApiResponse(data=task.to_dict())


@router.get("/optimization/tasks", response_model=ApiResponse[dict])
async def list_optimization_tasks(project_id: str | None = None):
    tasks = _optimizer.list_tasks(project_id)
    return ApiResponse(data={
        "total": len(tasks),
        "tasks": [t.to_dict() for t in tasks],
    })


@router.get("/optimization/builtins/objectives", response_model=ApiResponse[dict])
async def list_builtin_objectives():
    return ApiResponse(data={
        "objectives": {k: v.to_dict() for k, v in BUILTIN_OBJECTIVES.items()},
    })


@router.get("/optimization/builtins/constraints", response_model=ApiResponse[dict])
async def list_builtin_constraints():
    return ApiResponse(data={
        "constraints": {k: v.to_dict() for k, v in BUILTIN_CONSTRAINTS.items()},
    })


@router.get("/optimization/builtins/variables", response_model=ApiResponse[dict])
async def list_builtin_variables():
    return ApiResponse(data={
        "variables": {k: v.to_dict() for k, v in BUILTIN_DESIGN_VARIABLES.items()},
    })