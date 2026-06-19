from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.services.generative_design.uncertainty_quantification_service import (
    UncertaintyQuantificationService,
    UQMethodSpec,
    UQMethodType,
)
from src.domain.services.generative_design.seven_discipline_mdo_service import (
    SevenDisciplineMDOService,
    MDOConfig7D,
)

router = APIRouter(prefix="/api/v6/physics-twin", tags=["UQ & 7-Discipline MDO v6"])

_uq_service = UncertaintyQuantificationService()
_mdo7d_service = SevenDisciplineMDOService()


@router.post("/cfd-surrogate-models/predict-with-uq")
async def predict_with_uq(body: dict[str, Any]):
    inputs = body.get("inputs", {})
    method = body.get("method", "")
    try:
        result = _uq_service.predictWithUQ(inputs=inputs, method=method)
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/uq-methods")
async def register_uq_method(body: dict[str, Any]):
    spec = UQMethodSpec(
        method_id=body.get("method_id", ""),
        method_type=UQMethodType(body.get("method_type", "MCDropout")),
        surrogate_model_id=body.get("surrogate_model_id", ""),
        hyperparameters=body.get("hyperparameters", {}),
        confidence_level=body.get("confidence_level", 0.95),
        cov_threshold=body.get("cov_threshold", 0.10),
    )
    try:
        method_id = _uq_service.registerUQMethod(spec=spec)
        return {"method_id": method_id, "registered": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/uq-methods/{method_id}/hot-swap")
async def hot_swap_uq_method(method_id: str):
    try:
        result = _uq_service.hotSwapUQMethod(method_id=method_id)
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/mdo-runs/{run_id}/propagate-uncertainty")
async def propagate_uncertainty_through_mdo(run_id: str):
    result = _uq_service.propagateUncertaintyThroughMDO(run_id=run_id)
    return result.to_dict()


@router.post("/mdo-runs/7-discipline")
async def run_7_discipline_mdo(body: dict[str, Any]):
    config = MDOConfig7D(
        requirement_id=body.get("requirement_id", ""),
        discipline_config=body.get("discipline_config", {}),
        objectives=body.get("objectives", {}),
        constraints_config=body.get("constraints_config", {}),
        design_variables=body.get("design_variables", {}),
        population_size=body.get("population_size", 100),
        max_generations=body.get("max_generations", 300),
        active_discipline_count=body.get("active_discipline_count", 7),
    )
    solution = _mdo7d_service.run7DisciplineMDO(config=config)
    return solution.to_dict()


@router.post("/mdo-discipline-solvers")
async def register_discipline_solver(body: dict[str, Any]):
    from src.domain.services.generative_design.seven_discipline_mdo_service import (
        CostSolver,
        ManufacturingSolver,
        CertificationSolver,
    )
    name = body.get("name", "")
    solver_map = {
        "Cost": CostSolver,
        "Manufacturing": ManufacturingSolver,
        "Certification": CertificationSolver,
    }
    if name in solver_map:
        solver_id = _mdo7d_service.registerDisciplineSolver(solver_map[name]())
        return {"solver_id": solver_id, "registered": True}
    return {"registered": False, "error": f"Unknown solver: {name}"}


@router.get("/mdo-runs/{run_id}/7-discipline-sensitivity")
async def get_7_discipline_sensitivity(run_id: str):
    try:
        result = _mdo7d_service.getDisciplineSensitivity(run_id=run_id)
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))