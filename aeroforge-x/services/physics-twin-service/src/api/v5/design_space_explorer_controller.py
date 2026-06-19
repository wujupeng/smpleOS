from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.services.generative_design.design_space_explorer_service import (
    DesignSpaceExplorerService,
    MDOOptimizerService,
)

router = APIRouter(prefix="/api/v5/physics-twin/design-space", tags=["Design Space Explorer v5"])

_mdo_service = MDOOptimizerService()
_service = DesignSpaceExplorerService(mdo_service=_mdo_service)


@router.post("/pareto-visualize")
async def visualize_pareto_front(body: dict[str, Any]):
    run_id = body.get("run_id", "")
    dimensions = body.get("dimensions", ["L_D", "total_weight_kg"])

    result = _service.visualize_pareto_front(run_id=run_id, dimensions=dimensions)
    if result is None:
        raise HTTPException(status_code=404, detail="No Pareto front found for this run")

    return {
        "run_id": result.run_id,
        "dimensions": result.dimensions,
        "point_count": len(result.points),
        "pareto_point_count": len(result.pareto_points),
        "points": result.points,
        "pareto_points": result.pareto_points,
    }


@router.post("/pareto-filter")
async def filter_pareto_solutions(body: dict[str, Any]):
    run_id = body.get("run_id", "")
    filters = body.get("filters", {})

    solutions = _service.filter_pareto_solutions(run_id=run_id, filters=filters)
    return {
        "run_id": run_id,
        "filtered_count": len(solutions),
        "solutions": [s.to_dict() for s in solutions],
    }


@router.get("/{run_id}/correlation-heatmap")
async def compute_correlation_heatmap(run_id: str):
    result = _service.compute_correlation_heatmap(run_id=run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Insufficient data for correlation analysis")

    return {
        "run_id": result.run_id,
        "variables": result.variables,
        "matrix": result.matrix,
    }


@router.post("/export")
async def export_selected_designs(body: dict[str, Any]):
    solution_ids = body.get("solution_ids", [])
    run_id = body.get("run_id", "")

    result = _service.export_selected_designs(solution_ids=solution_ids, run_id=run_id)
    return {
        "solution_ids": result.solution_ids,
        "success": result.success,
        "configurations": result.configurations,
    }


@router.get("/history/{requirement_id}")
async def get_exploration_history(requirement_id: str):
    history = _service.get_exploration_history(requirement_id=requirement_id)
    return {
        "requirement_id": requirement_id,
        "steps": [
            {
                "step_id": step.step_id,
                "action_type": step.action_type,
                "action_params": step.action_params,
                "result_snapshot": step.result_snapshot,
            }
            for step in history
        ],
    }


@router.post("/revert")
async def revert_to_design_point(body: dict[str, Any]):
    step_id = body.get("step_id", "")
    requirement_id = body.get("requirement_id", "")

    result = _service.revert_to_design_point(step_id=step_id, requirement_id=requirement_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Design point not found")

    return {"step_id": step_id, "reverted_configuration": result}