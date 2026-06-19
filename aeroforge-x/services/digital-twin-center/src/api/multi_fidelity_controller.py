from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from aeroforge_common.domain.responses import ApiResponse

from ..domain.services.reduced_order_model_service import (
    FidelityLevel,
    MultiFidelityService,
    ReducedOrderModelService,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/twins/simulation", tags=["Multi-Fidelity Simulation"])

_rom_service = ReducedOrderModelService()
_mf_service = MultiFidelityService()


class BuildROMRequest(BaseModel):
    rom_type: str = Field(..., description="aerodynamic|structural|thermal")
    high_fidelity_results: list[dict[str, Any]] = []
    basis_dimension: int = 10


class RunROMSimulationRequest(BaseModel):
    model_id: str = Field(..., min_length=1)
    parameters: dict[str, Any] = {}


class RunMultiFidelityRequest(BaseModel):
    model_id: str | None = None
    parameters: dict[str, Any] = {}
    fidelity_level: str = Field(default="rom", description="rom|medium|high")


class SelectFidelityRequest(BaseModel):
    simulation_type: str = Field(..., min_length=1)
    required_accuracy: float = 95.0
    max_time_seconds: float = 60.0


class UpdateROMRequest(BaseModel):
    model_id: str = Field(..., min_length=1)
    new_results: list[dict[str, Any]] = []


@router.post("/rom/build", response_model=ApiResponse[dict])
async def build_rom(body: BuildROMRequest):
    model = _rom_service.build_reduced_order_model(
        rom_type=body.rom_type,
        high_fidelity_results=body.high_fidelity_results,
        basis_dimension=body.basis_dimension,
    )
    return ApiResponse(data=model.to_dict())


@router.post("/rom/run", response_model=ApiResponse[dict])
async def run_rom_simulation(body: RunROMSimulationRequest):
    try:
        result = _rom_service.run_reduced_simulation(body.model_id, body.parameters)
        return ApiResponse(data=result.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/rom/update", response_model=ApiResponse[dict])
async def update_rom(body: UpdateROMRequest):
    try:
        model = _rom_service.update_rom_from_high_fidelity(body.model_id, body.new_results)
        return ApiResponse(data=model.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/rom/models", response_model=ApiResponse[dict])
async def list_rom_models(rom_type: str | None = None):
    models = _rom_service.list_models(rom_type)
    return ApiResponse(data={"total": len(models), "models": [m.to_dict() for m in models]})


@router.post("/fidelity/select", response_model=ApiResponse[dict])
async def select_fidelity_level(body: SelectFidelityRequest):
    result = _mf_service.select_fidelity_level(
        body.simulation_type, body.required_accuracy, body.max_time_seconds,
    )
    return ApiResponse(data=result)


@router.post("/fidelity/run", response_model=ApiResponse[dict])
async def run_multi_fidelity_simulation(body: RunMultiFidelityRequest):
    try:
        result = _mf_service.run_multi_fidelity_simulation(
            model_id=body.model_id,
            parameters=body.parameters,
            fidelity_level=body.fidelity_level,
        )
        return ApiResponse(data=result.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))