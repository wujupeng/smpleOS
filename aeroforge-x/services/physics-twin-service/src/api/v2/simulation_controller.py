from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

from src.domain.enums import SolverType
from src.domain.services.simulation_execution_service import SimulationExecutionService
from src.infrastructure.database import get_pg_pool

router = APIRouter()


class SubmitSimulationRequest(BaseModel):
    model_id: str
    solver_type: SolverType
    boundary_conditions: dict[str, Any] | None = None
    config: dict[str, Any] | None = None


class RetrySimulationRequest(BaseModel):
    config_overrides: dict[str, Any] | None = None


@router.post("/simulations")
async def submit_simulation(req: SubmitSimulationRequest):
    pool = await get_pg_pool()
    try:
        sim = await SimulationExecutionService.submit_simulation(
            model_id=req.model_id, solver_type=req.solver_type,
            boundary_conditions=req.boundary_conditions, config=req.config, pool=pool,
        )
        return sim.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/simulations/{simulation_id}")
async def get_simulation_status(simulation_id: str):
    pool = await get_pg_pool()
    result = await SimulationExecutionService.get_simulation_status(simulation_id, pool)
    if result is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return result


@router.post("/simulations/{simulation_id}/cancel")
async def cancel_simulation(simulation_id: str):
    pool = await get_pg_pool()
    return await SimulationExecutionService.cancel_simulation(simulation_id, pool)


@router.post("/simulations/{simulation_id}/retry")
async def retry_simulation(simulation_id: str, req: RetrySimulationRequest | None = None):
    pool = await get_pg_pool()
    return await SimulationExecutionService.retry_simulation(
        simulation_id, config_overrides=req.config_overrides if req else None, pool=pool,
    )


@router.get("/simulations/{simulation_id}/results")
async def get_results(simulation_id: str):
    pool = await get_pg_pool()
    result = await SimulationExecutionService.get_results(simulation_id, pool)
    if result is None:
        raise HTTPException(status_code=404, detail="Simulation results not found")
    return result