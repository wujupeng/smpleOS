from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from aeroforge_common.domain.responses import ApiResponse

from ..domain.services.twin_loop_service import TwinLoopService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/twins", tags=["Twin Loop Feedback"])

_service = TwinLoopService()


class FlightToDesignRequest(BaseModel):
    flight_data: dict[str, Any]
    design_data: dict[str, Any]


class MfgToDesignRequest(BaseModel):
    manufacturing_data: dict[str, Any]
    design_data: dict[str, Any]


class FlightToMaintRequest(BaseModel):
    flight_data: dict[str, Any]
    maintenance_data: dict[str, Any]


class MaintToMfgRequest(BaseModel):
    maintenance_data: dict[str, Any]
    manufacturing_data: dict[str, Any]


@router.get("/{aircraft_sn}/loop/flight-to-design", response_model=ApiResponse[dict])
async def feedback_flight_to_design(aircraft_sn: str, flight_data: str = "{}", design_data: str = "{}"):
    import json
    try:
        fd = json.loads(flight_data)
        dd = json.loads(design_data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON data")
    feedbacks = _service.feedback_flight_to_design(aircraft_sn, fd, dd)
    return ApiResponse(data={"aircraft_sn": aircraft_sn, "feedbacks": [f.to_dict() for f in feedbacks], "total": len(feedbacks)})


@router.post("/{aircraft_sn}/loop/flight-to-design", response_model=ApiResponse[dict])
async def feedback_flight_to_design_post(aircraft_sn: str, body: FlightToDesignRequest):
    feedbacks = _service.feedback_flight_to_design(aircraft_sn, body.flight_data, body.design_data)
    return ApiResponse(data={"aircraft_sn": aircraft_sn, "feedbacks": [f.to_dict() for f in feedbacks], "total": len(feedbacks)})


@router.post("/{aircraft_sn}/loop/mfg-to-design", response_model=ApiResponse[dict])
async def feedback_mfg_to_design(aircraft_sn: str, body: MfgToDesignRequest):
    feedbacks = _service.feedback_manufacturing_to_design(aircraft_sn, body.manufacturing_data, body.design_data)
    return ApiResponse(data={"aircraft_sn": aircraft_sn, "feedbacks": [f.to_dict() for f in feedbacks], "total": len(feedbacks)})


@router.post("/{aircraft_sn}/loop/flight-to-maint", response_model=ApiResponse[dict])
async def feedback_flight_to_maint(aircraft_sn: str, body: FlightToMaintRequest):
    feedbacks = _service.feedback_flight_to_maintenance(aircraft_sn, body.flight_data, body.maintenance_data)
    return ApiResponse(data={"aircraft_sn": aircraft_sn, "feedbacks": [f.to_dict() for f in feedbacks], "total": len(feedbacks)})


@router.post("/{aircraft_sn}/loop/maint-to-mfg", response_model=ApiResponse[dict])
async def feedback_maint_to_mfg(aircraft_sn: str, body: MaintToMfgRequest):
    feedbacks = _service.feedback_maintenance_to_manufacturing(aircraft_sn, body.maintenance_data, body.manufacturing_data)
    return ApiResponse(data={"aircraft_sn": aircraft_sn, "feedbacks": [f.to_dict() for f in feedbacks], "total": len(feedbacks)})


@router.get("/{aircraft_sn}/loop/report", response_model=ApiResponse[dict])
async def get_loop_report(aircraft_sn: str):
    report = _service.generate_loop_report(aircraft_sn)
    return ApiResponse(data=report.to_dict())


@router.get("/{aircraft_sn}/loop/feedbacks", response_model=ApiResponse[dict])
async def get_loop_feedbacks(aircraft_sn: str, source: str | None = None, target: str | None = None):
    feedbacks = _service.get_feedbacks(aircraft_sn, source, target)
    return ApiResponse(data={"aircraft_sn": aircraft_sn, "feedbacks": feedbacks, "total": len(feedbacks)})