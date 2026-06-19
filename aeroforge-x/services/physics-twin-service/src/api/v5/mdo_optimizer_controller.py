from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.services.generative_design.mdo_optimizer_service import (
    MDOOptimizerService,
    MDOConfig,
)

router = APIRouter(prefix="/api/v5/physics-twin/mdo-runs", tags=["MDO Optimizer v5"])

_service = MDOOptimizerService()


@router.post("")
async def run_mdo(body: dict[str, Any]):
    config = MDOConfig(
        requirement_id=body.get("requirement_id", ""),
        objectives=body.get("objectives", []),
        constraints_config=body.get("constraints_config", []),
        design_variables=body.get("design_variables", []),
        population_size=body.get("population_size", 100),
        max_generations=body.get("max_generations", 200),
    )

    run_id = _service.run_mdo(config=config)
    convergence = _service.get_convergence_status(run_id)

    return {
        "run_id": run_id,
        "status": convergence.status.value if convergence else "Running",
        "pareto_size": convergence.pareto_size if convergence else 0,
        "best_objectives": convergence.best_objectives if convergence else {},
    }


@router.get("/{run_id}/pareto-front")
async def get_pareto_front(run_id: str):
    pareto = _service.get_pareto_front(run_id)
    return {
        "run_id": run_id,
        "pareto_size": len(pareto),
        "solutions": [s.to_dict() for s in pareto],
    }


@router.get("/{run_id}/sensitivity")
async def compute_sensitivity(run_id: str):
    result = _service.compute_sensitivity(run_id)
    return {
        "run_id": result.run_id,
        "first_order": result.first_order,
        "total_order": result.total_order,
    }


@router.get("/{run_id}/convergence")
async def get_convergence(run_id: str):
    report = _service.get_convergence_status(run_id)
    if report is None:
        raise HTTPException(status_code=404, detail="MDO run not found")
    return {
        "run_id": report.run_id,
        "status": report.status.value,
        "hypervolume_history": report.hypervolume_history,
        "pareto_size": report.pareto_size,
        "generations_completed": report.generations_completed,
        "best_objectives": report.best_objectives,
    }