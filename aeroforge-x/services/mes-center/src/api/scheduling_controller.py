from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from aeroforge_common.domain.responses import ApiResponse

from ..domain.entities.production_schedule import (
    ObjectiveFunction, ConstraintType, ConstraintPriority,
)
from ..domain.services.scheduling_domain_service import SchedulingDomainService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/mes", tags=["MES - Scheduling"])

_service = SchedulingDomainService()


class CreateScheduleRequest(BaseModel):
    tenant_id: str = Field(default="default")
    project_id: str = Field(default="default")
    name: str = Field(..., min_length=1)
    schedule_horizon_start: str = ""
    schedule_horizon_end: str = ""
    objective_function: ObjectiveFunction = ObjectiveFunction.MIN_MAKESPAN
    created_by: str = ""


class AddWorkOrderRequest(BaseModel):
    work_order_id: str = Field(..., min_length=1)
    work_order_code: str = ""
    priority: int = 0
    due_date: str = ""
    operations: list[dict[str, Any]] = Field(default_factory=list)


class AddResourceRequest(BaseModel):
    resource_id: str = Field(..., min_length=1)
    resource_name: str = ""
    resource_type: str = "workstation"
    capacity: int = 1
    skills: list[str] = Field(default_factory=list)
    available_from: int = 0
    available_to: int = 240


class AddConstraintRequest(BaseModel):
    constraint_type: ConstraintType
    constraint_expression: str
    priority: ConstraintPriority = ConstraintPriority.HARD
    description: str = ""


class WhatIfRequest(BaseModel):
    add_work_orders: list[dict[str, Any]] = Field(default_factory=list)
    resource_changes: list[dict[str, Any]] = Field(default_factory=list)


@router.post("/schedules", response_model=ApiResponse[dict])
async def create_schedule(body: CreateScheduleRequest):
    schedule = _service.create_schedule(
        tenant_id=body.tenant_id,
        project_id=body.project_id,
        name=body.name,
        schedule_horizon_start=body.schedule_horizon_start,
        schedule_horizon_end=body.schedule_horizon_end,
        objective_function=body.objective_function,
        created_by=body.created_by,
    )
    return ApiResponse(data=schedule.to_dict())


@router.post("/schedules/{schedule_id}/work-orders", response_model=ApiResponse[dict])
async def add_work_order(schedule_id: str, body: AddWorkOrderRequest):
    schedule = _service.add_work_order(
        schedule_id=schedule_id,
        work_order_id=body.work_order_id,
        work_order_code=body.work_order_code,
        priority=body.priority,
        due_date=body.due_date,
        operations=body.operations,
    )
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return ApiResponse(data=schedule.to_dict())


@router.post("/schedules/{schedule_id}/resources", response_model=ApiResponse[dict])
async def add_resource(schedule_id: str, body: AddResourceRequest):
    schedule = _service.add_resource(
        schedule_id=schedule_id,
        resource_id=body.resource_id,
        resource_name=body.resource_name,
        resource_type=body.resource_type,
        capacity=body.capacity,
        skills=body.skills,
        available_from=body.available_from,
        available_to=body.available_to,
    )
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return ApiResponse(data=schedule.to_dict())


@router.post("/schedules/{schedule_id}/constraints", response_model=ApiResponse[dict])
async def add_constraint(schedule_id: str, body: AddConstraintRequest):
    schedule = _service.add_constraint(
        schedule_id=schedule_id,
        constraint_type=body.constraint_type,
        constraint_expression=body.constraint_expression,
        priority=body.priority,
        description=body.description,
    )
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return ApiResponse(data=schedule.to_dict())


@router.post("/schedules/{schedule_id}/optimize", response_model=ApiResponse[dict])
async def optimize_schedule(schedule_id: str):
    schedule = _service.optimize_schedule(schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return ApiResponse(data=schedule.to_dict())


@router.get("/schedules/{schedule_id}", response_model=ApiResponse[dict])
async def get_schedule(schedule_id: str):
    schedule = _service.get_schedule(schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return ApiResponse(data=schedule.to_dict())


@router.get("/schedules/{schedule_id}/gantt", response_model=ApiResponse[dict])
async def get_gantt_data(schedule_id: str):
    gantt = _service.export_gantt_data(schedule_id)
    if gantt is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return ApiResponse(data={"gantt_data": gantt})


@router.get("/schedules/{schedule_id}/conflicts", response_model=ApiResponse[dict])
async def detect_conflicts(schedule_id: str):
    conflicts = _service.detect_conflicts(schedule_id)
    return ApiResponse(data={"conflicts": conflicts, "total": len(conflicts)})


@router.post("/schedules/{schedule_id}/what-if", response_model=ApiResponse[dict])
async def what_if_analysis(schedule_id: str, body: WhatIfRequest):
    result = _service.what_if_analysis(schedule_id, body.model_dump())
    if result is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return ApiResponse(data=result)


@router.get("/schedules", response_model=ApiResponse[dict])
async def list_schedules(
    tenant_id: str | None = None,
    project_id: str | None = None,
):
    schedules = _service.list_schedules(tenant_id, project_id)
    return ApiResponse(data={
        "total": len(schedules),
        "schedules": [s.to_dict() for s in schedules],
    })