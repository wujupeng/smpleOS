from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from aeroforge_common.domain.base import AggregateRoot, DomainEvent


class ParametricSweepType(str, Enum):
    ANGLE_OF_ATTACK = "angle_of_attack"
    MACH_NUMBER = "mach_number"
    REYNOLDS_NUMBER = "reynolds_number"
    SIDESLIP = "sideslip"


class ParametricStudyStatus(str, Enum):
    QUEUED = "queued"
    GENERATING_CASES = "generating_cases"
    RUNNING = "running"
    POST_PROCESSING = "post_processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AdjointOptStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SENSITIVITY_COMPUTED = "sensitivity_computed"
    GEOMETRY_UPDATED = "geometry_updated"
    COMPLETED = "completed"
    FAILED = "failed"


class AeroDatabaseStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SweepRange:
    parameter: str
    start: float
    end: float
    step: float
    unit: str = ""

    def to_points(self) -> list[float]:
        points = []
        current = self.start
        while current <= self.end + 1e-10:
            points.append(round(current, 6))
            current += self.step
        return points

    def to_dict(self) -> dict[str, Any]:
        return {
            "parameter": self.parameter,
            "start": self.start,
            "end": self.end,
            "step": self.step,
            "unit": self.unit,
            "num_points": len(self.to_points()),
        }


@dataclass
class CaseResult:
    case_id: str
    parameters: dict[str, float]
    lift_coefficient: float = 0.0
    drag_coefficient: float = 0.0
    moment_coefficient: float = 0.0
    convergence_status: str = "not_converged"
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "parameters": self.parameters,
            "lift_coefficient": self.lift_coefficient,
            "drag_coefficient": self.drag_coefficient,
            "moment_coefficient": self.moment_coefficient,
            "convergence_status": self.convergence_status,
            "error_message": self.error_message,
        }


class ParametricStudy(AggregateRoot):
    def __init__(
        self,
        model_id: str,
        project_id: str = "default",
        tenant_id: str = "default",
        sweep_ranges: list[SweepRange] | None = None,
        solver: str = "simpleFoam",
        turbulence_model: str = "kOmegaSST",
        max_parallel_cases: int = 4,
        task_id: str | None = None,
    ) -> None:
        super().__init__(task_id)
        self.model_id = model_id
        self.project_id = project_id
        self.tenant_id = tenant_id
        self.sweep_ranges: list[SweepRange] = sweep_ranges or []
        self.solver = solver
        self.turbulence_model = turbulence_model
        self.max_parallel_cases = max_parallel_cases
        self.status = ParametricStudyStatus.QUEUED
        self.case_results: list[CaseResult] = []
        self.total_cases = 0
        self.completed_cases = 0
        self.failed_cases = 0
        self.error_message: str | None = None
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        self.completed_at: datetime | None = None

    def calculate_total_cases(self) -> int:
        if not self.sweep_ranges:
            return 0
        total = 1
        for sr in self.sweep_ranges:
            total *= len(sr.to_points())
        self.total_cases = total
        return total

    def add_case_result(self, result: CaseResult) -> None:
        self.case_results.append(result)
        if result.convergence_status == "converged":
            self.completed_cases += 1
        else:
            self.failed_cases += 1
        self.updated_at = datetime.now(timezone.utc)

    def complete_study(self) -> None:
        self.status = ParametricStudyStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        self.add_domain_event(DomainEvent(
            event_type="cae.parametric_study.completed",
            aggregate_id=self.id,
            payload={"task_id": self.id, "model_id": self.model_id,
                     "total_cases": self.total_cases, "completed": self.completed_cases},
        ))

    def fail(self, error: str) -> None:
        self.status = ParametricStudyStatus.FAILED
        self.error_message = error
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "model_id": self.model_id,
            "project_id": self.project_id,
            "tenant_id": self.tenant_id,
            "sweep_ranges": [sr.to_dict() for sr in self.sweep_ranges],
            "solver": self.solver,
            "turbulence_model": self.turbulence_model,
            "max_parallel_cases": self.max_parallel_cases,
            "status": self.status.value,
            "case_results": [cr.to_dict() for cr in self.case_results],
            "total_cases": self.total_cases,
            "completed_cases": self.completed_cases,
            "failed_cases": self.failed_cases,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class AdjointIteration:
    iteration: int
    objective_value: float
    sensitivity_norm: float
    geometry_update_norm: float
    converged: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "iteration": self.iteration,
            "objective_value": self.objective_value,
            "sensitivity_norm": self.sensitivity_norm,
            "geometry_update_norm": self.geometry_update_norm,
            "converged": self.converged,
        }


class AdjointOptimization(AggregateRoot):
    def __init__(
        self,
        model_id: str,
        project_id: str = "default",
        tenant_id: str = "default",
        objective_function: str = "minimize_drag",
        max_iterations: int = 20,
        convergence_tolerance: float = 1e-4,
        step_size: float = 0.01,
        task_id: str | None = None,
    ) -> None:
        super().__init__(task_id)
        self.model_id = model_id
        self.project_id = project_id
        self.tenant_id = tenant_id
        self.objective_function = objective_function
        self.max_iterations = max_iterations
        self.convergence_tolerance = convergence_tolerance
        self.step_size = step_size
        self.status = AdjointOptStatus.QUEUED
        self.iterations: list[AdjointIteration] = []
        self.current_iteration = 0
        self.initial_objective: float | None = None
        self.final_objective: float | None = None
        self.improvement_pct: float = 0.0
        self.error_message: str | None = None
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def add_iteration(self, iteration: AdjointIteration) -> None:
        self.iterations.append(iteration)
        self.current_iteration = iteration.iteration
        self.status = AdjointOptStatus.SENSITIVITY_COMPUTED
        self.updated_at = datetime.now(timezone.utc)

    def complete(self) -> None:
        self.status = AdjointOptStatus.COMPLETED
        if self.iterations:
            self.initial_objective = self.iterations[0].objective_value
            self.final_objective = self.iterations[-1].objective_value
            if self.initial_objective and self.initial_objective != 0:
                self.improvement_pct = abs(
                    (self.final_objective - self.initial_objective) / self.initial_objective * 100
                )
        self.updated_at = datetime.now(timezone.utc)
        self.add_domain_event(DomainEvent(
            event_type="cae.adjoint_optimization.completed",
            aggregate_id=self.id,
            payload={"task_id": self.id, "model_id": self.model_id,
                     "improvement_pct": self.improvement_pct},
        ))

    def fail(self, error: str) -> None:
        self.status = AdjointOptStatus.FAILED
        self.error_message = error
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "model_id": self.model_id,
            "project_id": self.project_id,
            "tenant_id": self.tenant_id,
            "objective_function": self.objective_function,
            "max_iterations": self.max_iterations,
            "convergence_tolerance": self.convergence_tolerance,
            "step_size": self.step_size,
            "status": self.status.value,
            "iterations": [it.to_dict() for it in self.iterations],
            "current_iteration": self.current_iteration,
            "initial_objective": self.initial_objective,
            "final_objective": self.final_objective,
            "improvement_pct": self.improvement_pct,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class AeroDatabasePoint:
    angle_of_attack: float
    mach_number: float
    sideslip_angle: float
    cl: float = 0.0
    cd: float = 0.0
    cm: float = 0.0
    convergence: str = "not_converged"

    def to_dict(self) -> dict[str, Any]:
        return {
            "alpha": self.angle_of_attack,
            "mach": self.mach_number,
            "beta": self.sideslip_angle,
            "cl": self.cl,
            "cd": self.cd,
            "cm": self.cm,
            "convergence": self.convergence,
        }


class AeroDatabase(AggregateRoot):
    def __init__(
        self,
        model_id: str,
        project_id: str = "default",
        tenant_id: str = "default",
        alpha_range: SweepRange | None = None,
        mach_range: SweepRange | None = None,
        beta_range: SweepRange | None = None,
        task_id: str | None = None,
    ) -> None:
        super().__init__(task_id)
        self.model_id = model_id
        self.project_id = project_id
        self.tenant_id = tenant_id
        self.alpha_range = alpha_range
        self.mach_range = mach_range
        self.beta_range = beta_range
        self.status = AeroDatabaseStatus.QUEUED
        self.data_points: list[AeroDatabasePoint] = []
        self.total_points = 0
        self.completed_points = 0
        self.error_message: str | None = None
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def calculate_total_points(self) -> int:
        alpha_pts = len(self.alpha_range.to_points()) if self.alpha_range else 1
        mach_pts = len(self.mach_range.to_points()) if self.mach_range else 1
        beta_pts = len(self.beta_range.to_points()) if self.beta_range else 1
        self.total_points = alpha_pts * mach_pts * beta_pts
        return self.total_points

    def add_data_point(self, point: AeroDatabasePoint) -> None:
        self.data_points.append(point)
        self.completed_points += 1
        self.updated_at = datetime.now(timezone.utc)

    def complete(self) -> None:
        self.status = AeroDatabaseStatus.COMPLETED
        self.updated_at = datetime.now(timezone.utc)
        self.add_domain_event(DomainEvent(
            event_type="cae.aero_database.completed",
            aggregate_id=self.id,
            payload={"task_id": self.id, "model_id": self.model_id,
                     "total_points": self.total_points},
        ))

    def fail(self, error: str) -> None:
        self.status = AeroDatabaseStatus.FAILED
        self.error_message = error
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "model_id": self.model_id,
            "project_id": self.project_id,
            "tenant_id": self.tenant_id,
            "alpha_range": self.alpha_range.to_dict() if self.alpha_range else None,
            "mach_range": self.mach_range.to_dict() if self.mach_range else None,
            "beta_range": self.beta_range.to_dict() if self.beta_range else None,
            "status": self.status.value,
            "data_points": [dp.to_dict() for dp in self.data_points],
            "total_points": self.total_points,
            "completed_points": self.completed_points,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }