from __future__ import annotations

import logging
import math
from typing import Any

from .multiphysics_task import (
    CoupledResult,
    CouplingScheme,
    CouplingType,
    ConvergenceCriteria,
    MultiphysicsResultSummary,
    MultiphysicsStatus,
    MultiphysicsTask,
    SolverStatus,
)

logger = logging.getLogger(__name__)


class CouplingOrchestrator:
    def __init__(self, convergence_criteria: ConvergenceCriteria) -> None:
        self._criteria = convergence_criteria
        self._iteration = 0
        self._convergence_history: list[dict[str, float]] = []
        self._solver_states: dict[str, dict[str, Any]] = {}

    def initialize_solvers(self, solver_names: list[str]) -> list[SolverStatus]:
        statuses = []
        for name in solver_names:
            self._solver_states[name] = {"status": "ready", "iteration": 0, "residual": 0.0}
            statuses.append(SolverStatus(solver_name=name, status="ready"))
        return statuses

    def run_coupling_iteration(self, iteration: int) -> dict[str, Any]:
        self._iteration = iteration
        iteration_data: dict[str, Any] = {"iteration": iteration, "solver_results": {}}

        for solver_name, state in self._solver_states.items():
            residual = 1.0 / (iteration + 1) ** 1.5 + 0.001 * math.sin(iteration)
            residual = max(residual, 1e-8)
            state["iteration"] = iteration
            state["residual"] = residual
            state["status"] = "completed"
            iteration_data["solver_results"][solver_name] = {
                "residual": residual,
                "status": "completed",
            }

        coupling_residual = self._compute_coupling_residual(iteration)
        self._convergence_history.append({
            "iteration": iteration,
            "coupling_residual": coupling_residual,
        })

        iteration_data["coupling_residual"] = coupling_residual
        return iteration_data

    def exchange_boundary_conditions(
        self, coupling_type: CouplingType, iteration_data: dict[str, Any],
    ) -> dict[str, Any]:
        exchanged: dict[str, Any] = {}

        if coupling_type == CouplingType.AERO_STRUCTURAL:
            exchanged["cfd_to_fea"] = {"type": "pressure_load", "transferred": True}
            exchanged["fea_to_cfd"] = {"type": "mesh_deformation", "transferred": True}

        elif coupling_type == CouplingType.THERMAL_STRUCTURAL:
            exchanged["thermal_to_fea"] = {"type": "temperature_field", "transferred": True}
            exchanged["fea_to_thermal"] = {"type": "geometry_update", "transferred": True}

        elif coupling_type == CouplingType.AERO_THERMAL_STRUCTURAL:
            exchanged["cfd_to_thermal"] = {"type": "heat_source", "transferred": True}
            exchanged["thermal_to_fea"] = {"type": "temperature_field", "transferred": True}
            exchanged["fea_to_cfd"] = {"type": "mesh_deformation", "transferred": True}

        return exchanged

    def check_convergence(self) -> bool:
        if not self._convergence_history:
            return False
        last_residual = self._convergence_history[-1]["coupling_residual"]
        return last_residual < self._criteria.residual_tolerance

    def _compute_coupling_residual(self, iteration: int) -> float:
        base = 1.0 / (iteration + 1) ** 1.2
        noise = 0.005 * math.sin(iteration * 0.7)
        return max(base + noise, 1e-8)

    @property
    def convergence_history(self) -> list[dict[str, float]]:
        return self._convergence_history

    def get_solver_statuses(self) -> list[SolverStatus]:
        return [
            SolverStatus(
                solver_name=name,
                status=state.get("status", "unknown"),
                current_iteration=state.get("iteration", 0),
                residual=state.get("residual", 0.0),
            )
            for name, state in self._solver_states.items()
        ]


class MultiphysicsDomainService:
    def __init__(self) -> None:
        self._tasks: dict[str, MultiphysicsTask] = {}

    def submit_coupled_analysis(
        self,
        model_id: str,
        coupling_type: CouplingType = CouplingType.AERO_STRUCTURAL,
        coupling_scheme: CouplingScheme = CouplingScheme.EXPLICIT_WEAK,
        convergence_criteria: ConvergenceCriteria | None = None,
    ) -> MultiphysicsTask:
        task = MultiphysicsTask(
            model_id=model_id,
            coupling_type=coupling_type,
            coupling_scheme=coupling_scheme,
            convergence_criteria=convergence_criteria,
        )
        self._tasks[task.id] = task
        logger.info("Submitted multiphysics analysis: task=%s type=%s scheme=%s",
                     task.id, coupling_type.value, coupling_scheme.value)
        return task

    def orchestrate_solvers(self, task: MultiphysicsTask) -> MultiphysicsTask:
        task.start_running()

        criteria = task.convergence_criteria
        orchestrator = CouplingOrchestrator(criteria)
        solver_statuses = orchestrator.initialize_solvers(task.participant_solvers)

        max_iter = criteria.max_iterations
        if task.coupling_scheme == CouplingScheme.IMPLICIT_STRONG:
            max_iter = min(max_iter * 2, 50)

        converged = False
        iteration = 0

        for i in range(max_iter):
            iteration = i + 1
            progress = 10.0 + (80.0 * iteration / max_iter)
            task.update_progress(progress, f"coupling_iteration_{iteration}")

            if i == 0:
                task.start_converging()

            iteration_data = orchestrator.run_coupling_iteration(iteration)
            bc_exchanged = orchestrator.exchange_boundary_conditions(task.coupling_type, iteration_data)

            logger.debug("Coupling iteration %d: residual=%.6f bc=%s",
                         iteration, iteration_data["coupling_residual"], list(bc_exchanged.keys()))

            if orchestrator.check_convergence():
                converged = True
                break

        coupled_results = self._build_coupled_results(task, iteration)

        result = MultiphysicsResultSummary(
            converged=converged,
            iterations_completed=iteration,
            final_residual=orchestrator.convergence_history[-1]["coupling_residual"] if orchestrator.convergence_history else 0.0,
            coupled_results=coupled_results,
            convergence_history=orchestrator.convergence_history,
            solver_statuses=orchestrator.get_solver_statuses(),
        )

        task.complete(result)
        logger.info("Multiphysics analysis completed: task=%s converged=%s iterations=%d",
                     task.id, converged, iteration)
        return task

    def _build_coupled_results(self, task: MultiphysicsTask, iterations: int) -> CoupledResult:
        results = CoupledResult()

        if task.coupling_type in (CouplingType.AERO_STRUCTURAL, CouplingType.AERO_THERMAL_STRUCTURAL):
            results.aerodynamic_results = {
                "lift_coefficient": 0.45 + 0.01 * iterations,
                "drag_coefficient": 0.025 + 0.001 * iterations,
                "pressure_distribution": "coupled",
            }

        if task.coupling_type in (CouplingType.THERMAL_STRUCTURAL, CouplingType.AERO_THERMAL_STRUCTURAL):
            results.thermal_results = {
                "max_temperature_c": 85.0 - 0.5 * iterations,
                "heat_flux_max_w_m2": 15000.0,
            }

        results.structural_results = {
            "max_stress_pa": 150e6 + 5e6 * iterations,
            "max_deformation_m": 0.002 + 0.0001 * iterations,
            "safety_factor": 1.8 - 0.02 * iterations,
        }

        return results

    def get_task(self, task_id: str) -> MultiphysicsTask | None:
        return self._tasks.get(task_id)

    def list_tasks(self) -> list[MultiphysicsTask]:
        return list(self._tasks.values())