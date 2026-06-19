from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from aeroforge_common.domain.responses import ApiResponse

from ..domain.entities.topology_task import TopologyMethod
from ..domain.services.topology_optimizer import (
    TopologyOptimizer,
    BUILTIN_LOAD_CASES,
    BUILTIN_BOUNDARY_CONDITIONS,
    BUILTIN_DESIGN_REGIONS,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ai", tags=["Topology Optimization"])

_topology_optimizer = TopologyOptimizer()


class CreateTopologyRequest(BaseModel):
    project_id: str = Field(..., min_length=1)
    tenant_id: str = Field(default="default")
    design_region_names: list[str] = Field(default_factory=lambda: ["wing_box"])
    load_case_names: list[str] = Field(default_factory=lambda: ["wing_bending"])
    boundary_condition_names: list[str] = Field(default_factory=lambda: ["wing_root_fixed"])
    method: TopologyMethod = TopologyMethod.SIMP
    max_iterations: int = Field(default=50, ge=1, le=500)
    convergence_tolerance: float = Field(default=1e-4, gt=0)
    penalty_factor: float = Field(default=3.0, gt=0)
    filter_radius: float = Field(default=1.5, gt=0)


class RunTopologyRequest(BaseModel):
    task_id: str = Field(..., min_length=1)


@router.post("/topology/create", response_model=ApiResponse[dict])
async def create_topology_task(body: CreateTopologyRequest):
    task = _topology_optimizer.create_topology_task(
        project_id=body.project_id,
        tenant_id=body.tenant_id,
        design_region_names=body.design_region_names,
        load_case_names=body.load_case_names,
        boundary_condition_names=body.boundary_condition_names,
        method=body.method,
        max_iterations=body.max_iterations,
        convergence_tolerance=body.convergence_tolerance,
        penalty_factor=body.penalty_factor,
        filter_radius=body.filter_radius,
    )
    return ApiResponse(data=task.to_dict())


@router.post("/topology/run", response_model=ApiResponse[dict])
async def run_topology_optimization(body: RunTopologyRequest):
    task = _topology_optimizer.run_topology_optimization(body.task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Topology optimization task not found")
    return ApiResponse(data=task.to_dict())


@router.get("/topology/tasks/{task_id}", response_model=ApiResponse[dict])
async def get_topology_task(task_id: str):
    task = _topology_optimizer.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Topology optimization task not found")
    return ApiResponse(data=task.to_dict())


@router.get("/topology/tasks", response_model=ApiResponse[dict])
async def list_topology_tasks(project_id: str | None = None):
    tasks = _topology_optimizer.list_tasks(project_id)
    return ApiResponse(data={
        "total": len(tasks),
        "tasks": [t.to_dict() for t in tasks],
    })


@router.get("/topology/builtins/load-cases", response_model=ApiResponse[dict])
async def list_builtin_load_cases():
    return ApiResponse(data={
        "load_cases": {k: v.to_dict() for k, v in BUILTIN_LOAD_CASES.items()},
    })


@router.get("/topology/builtins/boundary-conditions", response_model=ApiResponse[dict])
async def list_builtin_boundary_conditions():
    return ApiResponse(data={
        "boundary_conditions": {k: v.to_dict() for k, v in BUILTIN_BOUNDARY_CONDITIONS.items()},
    })


@router.get("/topology/builtins/design-regions", response_model=ApiResponse[dict])
async def list_builtin_design_regions():
    return ApiResponse(data={
        "design_regions": {k: v.to_dict() for k, v in BUILTIN_DESIGN_REGIONS.items()},
    })