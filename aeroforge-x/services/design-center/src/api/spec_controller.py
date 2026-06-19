from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from aeroforge_db.pg import get_session
from aeroforge_common.domain.responses import ApiResponse, PagedResponse
from aeroforge_common.auth.models import AuthUser

from ..application.spec_application_service import SpecApplicationService
from ..infrastructure.persistence.spec_repository import SpecRepository

router = APIRouter(prefix="/api/v1/specs", tags=["AircraftSpec"])


class CreateSpecRequest(BaseModel):
    aircraft_type: str = Field(default="fixed_wing", description="飞行器类型: fixed_wing/glider/evtol/uav")
    payload_kg: float = Field(..., gt=0, description="载荷(kg)")
    range_km: float = Field(..., gt=0, description="航程(km)")
    cruise_speed_kmh: float = Field(..., gt=0, description="巡航速度(km/h)")
    takeoff_distance_m: float = Field(..., gt=0, description="起飞距离(m)")
    power_type: str = Field(default="electric", description="动力类型: electric/hybrid/gasoline/diesel")
    budget_cny: float | None = Field(None, description="预算(元)")
    material_id: str | None = Field(None, description="材料ID")
    certification_level_id: str | None = Field(None, description="认证等级ID")


class UpdateSpecRequest(BaseModel):
    aircraft_type: str | None = None
    payload_kg: float | None = None
    range_km: float | None = None
    cruise_speed_kmh: float | None = None
    takeoff_distance_m: float | None = None
    power_type: str | None = None
    budget_cny: float | None = None
    material_id: str | None = None
    certification_level_id: str | None = None


def _get_service(session: AsyncSession = Depends(get_session)) -> SpecApplicationService:
    repo = SpecRepository(session)
    return SpecApplicationService(repo)


def _get_current_user(request: Request) -> AuthUser:
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


@router.post("", response_model=ApiResponse[dict])
async def create_spec(
    body: CreateSpecRequest,
    request: Request,
    service: SpecApplicationService = Depends(_get_service),
):
    user = _get_current_user(request)
    spec = await service.create_spec(body.model_dump(), created_by=user.user_id)
    return ApiResponse(data=spec.to_dict())


@router.get("", response_model=PagedResponse[dict])
async def list_specs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: SpecApplicationService = Depends(_get_service),
):
    result = await service.list_specs(page=page, page_size=page_size)
    return PagedResponse(
        data=result["items"],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.get("/{spec_id}", response_model=ApiResponse[dict])
async def get_spec(
    spec_id: str,
    service: SpecApplicationService = Depends(_get_service),
):
    result = await service.get_spec(spec_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"AircraftSpec '{spec_id}' not found")
    return ApiResponse(data=result)


@router.put("/{spec_id}", response_model=ApiResponse[dict])
async def update_spec(
    spec_id: str,
    body: UpdateSpecRequest,
    service: SpecApplicationService = Depends(_get_service),
):
    result = await service.update_spec(spec_id, body.model_dump(exclude_none=True))
    if result is None:
        raise HTTPException(status_code=404, detail=f"AircraftSpec '{spec_id}' not found")
    return ApiResponse(data=result)


@router.post("/{spec_id}/confirm", response_model=ApiResponse[dict])
async def confirm_spec(
    spec_id: str,
    service: SpecApplicationService = Depends(_get_service),
):
    result = await service.confirm_spec(spec_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"AircraftSpec '{spec_id}' not found")
    return ApiResponse(data=result["spec"])


@router.post("/{spec_id}/validate", response_model=ApiResponse[dict])
async def validate_spec(
    spec_id: str,
    service: SpecApplicationService = Depends(_get_service),
):
    result = await service.validate_spec(spec_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"AircraftSpec '{spec_id}' not found")
    return ApiResponse(data=result)