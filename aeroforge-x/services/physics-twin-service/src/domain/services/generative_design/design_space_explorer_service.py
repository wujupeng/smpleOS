"""AeroForge-X v5.0 DesignSpaceExplorerService

Supports Pareto front visualization, filtering, correlation heatmap,
design export, and exploration history with revert capability.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from .mdo_optimizer_service import MDOOptimizerService, DesignSolution


@dataclass(frozen=True)
class VisualizationData:
    run_id: str
    dimensions: list[str]
    points: list[dict]
    pareto_points: list[dict]


@dataclass(frozen=True)
class CorrelationMatrix:
    run_id: str
    variables: list[str]
    matrix: list[list[float]]


@dataclass(frozen=True)
class ExportResult:
    solution_ids: list[str]
    configurations: list[dict]
    success: bool


@dataclass(frozen=True)
class ExplorationStep:
    step_id: str
    requirement_id: str
    action_type: str
    action_params: dict
    result_snapshot: dict


class DesignSpaceExplorerService:

    def __init__(self, mdo_service: MDOOptimizerService | None = None) -> None:
        self._mdo_service = mdo_service or MDOOptimizerService()
        self._exploration_history: dict[str, list[ExplorationStep]] = {}

    def visualize_pareto_front(
        self,
        run_id: str,
        dimensions: list[str],
    ) -> Optional[VisualizationData]:
        pareto = self._mdo_service.get_pareto_front(run_id)
        if not pareto:
            return None

        all_points = []
        pareto_points = []

        for sol in pareto:
            point: dict[str, float] = {}
            for dim in dimensions:
                if dim in sol.objective_values:
                    point[dim] = sol.objective_values[dim]
                elif dim in sol.design_parameters:
                    point[dim] = sol.design_parameters[dim]
            all_points.append(point)
            if sol.is_pareto_optimal:
                pareto_points.append(point)

        return VisualizationData(
            run_id=run_id,
            dimensions=dimensions,
            points=all_points,
            pareto_points=pareto_points,
        )

    def filter_pareto_solutions(
        self,
        run_id: str,
        filters: dict[str, dict],
    ) -> list[DesignSolution]:
        pareto = self._mdo_service.get_pareto_front(run_id)
        if not pareto:
            return []

        filtered = []
        for sol in pareto:
            passes = True
            for key, bounds in filters.items():
                value = sol.design_parameters.get(key) or sol.objective_values.get(key)
                if value is None:
                    passes = False
                    break
                if "min" in bounds and value < bounds["min"]:
                    passes = False
                    break
                if "max" in bounds and value > bounds["max"]:
                    passes = False
                    break
            if passes:
                filtered.append(sol)

        return filtered

    def compute_correlation_heatmap(self, run_id: str) -> Optional[CorrelationMatrix]:
        pareto = self._mdo_service.get_pareto_front(run_id)
        if not pareto or len(pareto) < 2:
            return None

        all_keys: set[str] = set()
        for sol in pareto:
            all_keys.update(sol.design_parameters.keys())
            all_keys.update(sol.objective_values.keys())

        variables = sorted(all_keys)
        n = len(variables)

        data: dict[str, list[float]] = {v: [] for v in variables}
        for sol in pareto:
            for v in variables:
                val = sol.design_parameters.get(v, sol.objective_values.get(v))
                data[v].append(val if val is not None else 0.0)

        matrix = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                arr_i = np.array(data[variables[i]])
                arr_j = np.array(data[variables[j]])
                if len(arr_i) > 1 and np.std(arr_i) > 0 and np.std(arr_j) > 0:
                    corr = np.corrcoef(arr_i, arr_j)[0, 1]
                    matrix[i][j] = float(corr) if not np.isnan(corr) else 0.0
                elif i == j:
                    matrix[i][j] = 1.0

        return CorrelationMatrix(
            run_id=run_id,
            variables=variables,
            matrix=matrix,
        )

    def export_selected_designs(
        self,
        solution_ids: list[str],
        run_id: str,
    ) -> ExportResult:
        pareto = self._mdo_service.get_pareto_front(run_id)
        selected = [s for s in pareto if s.solution_id in solution_ids]

        configurations = [s.to_dict() for s in selected]

        return ExportResult(
            solution_ids=solution_ids,
            configurations=configurations,
            success=len(selected) > 0,
        )

    def get_exploration_history(
        self,
        requirement_id: str,
    ) -> list[ExplorationStep]:
        return self._exploration_history.get(requirement_id, [])

    def revert_to_design_point(
        self,
        step_id: str,
        requirement_id: str,
    ) -> Optional[dict]:
        history = self._exploration_history.get(requirement_id, [])
        for step in history:
            if step.step_id == step_id:
                return step.result_snapshot
        return None

    def record_exploration_step(
        self,
        requirement_id: str,
        action_type: str,
        action_params: dict,
        result_snapshot: dict,
    ) -> ExplorationStep:
        step = ExplorationStep(
            step_id=f"EXP-{uuid.uuid4().hex[:8].upper()}",
            requirement_id=requirement_id,
            action_type=action_type,
            action_params=action_params,
            result_snapshot=result_snapshot,
        )

        self._exploration_history.setdefault(requirement_id, []).append(step)
        return step