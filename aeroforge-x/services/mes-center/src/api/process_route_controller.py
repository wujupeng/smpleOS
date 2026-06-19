from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from aeroforge_common.domain.responses import ApiResponse

from ..domain.services.process_route_domain_service import (
    ProcessRoute,
    ProcessRouteDomainService,
    PROCESS_TEMPLATES,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/mes/routes", tags=["Process Route"])

_route_service = ProcessRouteDomainService()
_route_store: dict[str, ProcessRoute] = {}


class GenerateRouteRequest(BaseModel):
    mbom_id: str
    mbom_data: dict[str, Any] = Field(default_factory=dict)
    created_by: str = ""


class UpdateRouteRequest(BaseModel):
    route_name: str | None = None
    operations: list[dict[str, Any]] | None = None


@router.post("/generate", response_model=ApiResponse[dict])
async def generate_route(body: GenerateRouteRequest):
    mbom_data = body.mbom_data or {"id": body.mbom_id, "mbom_code": body.mbom_id}
    route = _route_service.generate_from_mbom(mbom_data, body.created_by)
    _route_store[route.id] = route
    return ApiResponse(data=route.to_dict())


@router.get("/{route_id}", response_model=ApiResponse[dict])
async def get_route(route_id: str):
    route = _route_store.get(route_id)
    if route is None:
        raise HTTPException(status_code=404, detail="Process route not found")
    return ApiResponse(data=route.to_dict())


@router.put("/{route_id}", response_model=ApiResponse[dict])
async def update_route(route_id: str, body: UpdateRouteRequest):
    route = _route_store.get(route_id)
    if route is None:
        raise HTTPException(status_code=404, detail="Process route not found")

    if body.route_name:
        route.route_name = body.route_name

    if body.operations:
        from ..domain.services.process_route_domain_service import Operation, OperationType
        route.operations.clear()
        for seq, op_data in enumerate(body.operations, 1):
            op = Operation(
                operation_id=op_data.get("operation_id", f"OP-{seq:04d}"),
                operation_name=op_data.get("operation_name", ""),
                operation_type=OperationType(op_data.get("operation_type", "assembly")),
                sequence=seq,
                station=op_data.get("station", ""),
                equipment=op_data.get("equipment", ""),
                estimated_hours=op_data.get("estimated_hours", 0.0),
                dependencies=op_data.get("dependencies", []),
                is_quality_checkpoint=op_data.get("is_quality_checkpoint", False),
                is_mandatory_gate=op_data.get("is_mandatory_gate", False),
            )
            route.add_operation(op)

    return ApiResponse(data=route.to_dict())


@router.get("/templates", response_model=ApiResponse[dict])
async def get_route_templates():
    templates = []
    for key, tmpl in PROCESS_TEMPLATES.items():
        templates.append({
            "template_key": key,
            "template_name": tmpl["template_name"],
            "operation_count": len(tmpl["operations"]),
            "total_estimated_hours": sum(op.get("hours", 0) for op in tmpl["operations"]),
        })
    return ApiResponse(data={
        "total": len(templates),
        "templates": templates,
    })


@router.post("/{route_id}/publish", response_model=ApiResponse[dict])
async def publish_route(route_id: str):
    route = _route_store.get(route_id)
    if route is None:
        raise HTTPException(status_code=404, detail="Process route not found")
    try:
        route.publish()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ApiResponse(data={
        "route_id": route.id,
        "route_code": route.route_code,
        "status": route.status,
    })