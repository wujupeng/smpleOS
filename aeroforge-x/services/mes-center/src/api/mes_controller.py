from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from aeroforge_db.pg import get_session
from aeroforge_common.domain.responses import ApiResponse, PagedResponse

from ..application.mes_application_service import MesApplicationService
from ..infrastructure.mes_repository import SerialNumberRepository, StationRepository, WorkOrderRepository

router = APIRouter(prefix="/api/v1/mes", tags=["MES"])


class CreateWorkOrderRequest(BaseModel):
    product_model: str = Field(..., min_length=1)
    quantity: int = Field(1, gt=0)
    priority: str = Field("normal", pattern="^(low|normal|high|urgent)$")


class DispatchOrderRequest(BaseModel):
    station_id: str
    material_available: bool = True


class UpdateOrderStatusRequest(BaseModel):
    action: str = Field(..., pattern="^(start|progress|complete)$")
    progress: float | None = None


class AssignSerialRequest(BaseModel):
    item_code: str
    batch_number: str | None = None
    supplier: str | None = None


class LinkSerialRequest(BaseModel):
    work_order_id: str


def _get_service(session: AsyncSession = Depends(get_session)) -> MesApplicationService:
    return MesApplicationService(WorkOrderRepository(session), StationRepository(session), SerialNumberRepository(session))


@router.post("/orders", response_model=ApiResponse[dict])
async def create_work_order(body: CreateWorkOrderRequest, service: MesApplicationService = Depends(_get_service)):
    result = await service.create_work_order(body.product_model, body.quantity, body.priority, created_by="system")
    return ApiResponse(data=result)


@router.get("/orders", response_model=PagedResponse[dict])
async def list_work_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    service: MesApplicationService = Depends(_get_service),
):
    result = await service.list_work_orders(page=page, page_size=page_size, status=status)
    return PagedResponse(data=result["items"], total=result["total"], page=result["page"], page_size=result["page_size"])


@router.get("/orders/{order_id}", response_model=ApiResponse[dict])
async def get_work_order(order_id: str, service: MesApplicationService = Depends(_get_service)):
    result = await service.get_work_order(order_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Work order '{order_id}' not found")
    return ApiResponse(data=result)


@router.post("/orders/{order_id}/dispatch", response_model=ApiResponse[dict])
async def dispatch_work_order(order_id: str, body: DispatchOrderRequest, service: MesApplicationService = Depends(_get_service)):
    try:
        result = await service.dispatch_work_order(order_id, body.station_id, body.material_available)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail=f"Work order '{order_id}' not found")
    return ApiResponse(data=result)


@router.put("/orders/{order_id}/status", response_model=ApiResponse[dict])
async def update_order_status(order_id: str, body: UpdateOrderStatusRequest, service: MesApplicationService = Depends(_get_service)):
    try:
        result = await service.update_work_order_status(order_id, body.action, body.progress)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail=f"Work order '{order_id}' not found")
    return ApiResponse(data=result)


@router.get("/stations", response_model=ApiResponse[dict])
async def list_stations(service: MesApplicationService = Depends(_get_service)):
    result = await service.list_stations()
    return ApiResponse(data=result)


@router.get("/stations/{station_id}/status", response_model=ApiResponse[dict])
async def get_station_status(station_id: str, service: MesApplicationService = Depends(_get_service)):
    result = await service.get_station_status(station_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Station '{station_id}' not found")
    return ApiResponse(data=result)


@router.post("/serials/assign", response_model=ApiResponse[dict])
async def assign_serial_number(body: AssignSerialRequest, service: MesApplicationService = Depends(_get_service)):
    result = await service.assign_serial_number(body.item_code, body.batch_number, body.supplier)
    return ApiResponse(data=result)


@router.get("/serials/{sn}", response_model=ApiResponse[dict])
async def get_serial_number(sn: str, service: MesApplicationService = Depends(_get_service)):
    result = await service.get_serial_number(sn)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Serial number '{sn}' not found")
    return ApiResponse(data=result)


@router.put("/serials/{sn}/status", response_model=ApiResponse[dict])
async def link_serial_to_work_order(sn: str, body: LinkSerialRequest, service: MesApplicationService = Depends(_get_service)):
    result = await service.link_serial_to_work_order(sn, body.work_order_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Serial number '{sn}' not found")
    return ApiResponse(data=result)