from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from aeroforge_common.domain.responses import ApiResponse

from ..domain.services.material_trace_domain_service import MaterialTraceDomainService
from ..infrastructure.neo4j.trace_graph_repository import TraceGraphRepository

router = APIRouter(prefix="/api/v1", tags=["Trace"])


class RecordTraceRequest(BaseModel):
    supplier_code: str
    supplier_name: str
    batch_number: str
    item_code: str
    serial_number: str
    inspection_result: str = ""
    work_order_code: str | None = None
    aircraft_code: str | None = None
    installer: str | None = None


def _get_service() -> MaterialTraceDomainService:
    return MaterialTraceDomainService(TraceGraphRepository())


@router.post("/mes/trace/record", response_model=ApiResponse[dict])
async def record_trace(body: RecordTraceRequest, service: MaterialTraceDomainService = Depends(_get_service)):
    await service.record_trace(
        body.supplier_code, body.supplier_name, body.batch_number, body.item_code,
        body.serial_number, body.inspection_result, body.work_order_code, body.aircraft_code, body.installer,
    )
    return ApiResponse(data={"status": "recorded", "serial_number": body.serial_number})


@router.get("/trace/{serial_number}", response_model=ApiResponse[dict])
async def query_trace_chain(serial_number: str, service: MaterialTraceDomainService = Depends(_get_service)):
    result = await service.query_trace_chain(serial_number)
    return ApiResponse(data=result)


@router.get("/trace/batch/{batch_number}", response_model=ApiResponse[dict])
async def batch_forward_trace(batch_number: str, service: MaterialTraceDomainService = Depends(_get_service)):
    result = await service.batch_forward_trace(batch_number)
    return ApiResponse(data=result)


@router.get("/trace/integrity/{serial_number}", response_model=ApiResponse[dict])
async def check_trace_integrity(serial_number: str, service: MaterialTraceDomainService = Depends(_get_service)):
    result = await service.check_trace_integrity(serial_number)
    return ApiResponse(data=result)