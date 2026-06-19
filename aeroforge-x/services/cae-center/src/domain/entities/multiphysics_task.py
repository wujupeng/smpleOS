from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from aeroforge_common.domain.base import AggregateRoot, DomainEvent


class CouplingType(str, Enum):
    AERO_STRUCTURAL = "aero_structural"
    THERMAL_STRUCTURAL = "thermal_structural"
    AERO_THERMAL_STRUCTURAL = "aero_thermal_structural"


class CouplingScheme(str, Enum):
    EXPLICIT_WEAK = "explicit_weak"
    IMPLICIT_STRONG = "implicit_strong"


class MultiphysicsStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    CONVERGING = "converging"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ConvergenceCriteria:
    residual_tolerance: float = 1e-4
    max_iterations: int = 10
    relaxation_factor: float = 0.7

    def to_dict(self) -> dict[str, Any]:
        return {
            "residual_tolerance": self.residual_tolerance,
            "max_iterations": self.max_iterations,
            "relaxation_factor": self.relaxation_factor,
        }


@dataclass
class SolverStatus:
    solver_name: str
    status: str = "pending"
    current_iteration: int = 0
    residual: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "solver_name": self.solver_name,
            "status": self.status,
            "current_iteration": self.current_iteration,
            "residual": self.residual,
        }


@dataclass
class CoupledResult:
    thermal_results: dict[str, Any] = field(default_factory=dict)
    structural_results: dict[str, Any] = field(default_factory=dict)
    aerodynamic_results: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "thermal_results": self.thermal_results,
            "structural_results": self.structural_results,
            "aerodynamic_results": self.aerodynamic_results,
        }


@dataclass
class MultiphysicsResultSummary:
    converged: bool = False
    iterations_completed: int = 0
    final_residual: float = 0.0
    coupled_results: CoupledResult = field(default_factory=CoupledResult)
    convergence_history: list[dict[str, float]] = field(default_factory=list)
    solver_statuses: list[SolverStatus] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "converged": self.converged,
            "iterations_completed": self.iterations_completed,
            "final_residual": self.final_residual,
            "coupled_results": self.coupled_results.to_dict(),
            "convergence_history": self.convergence_history,
            "solver_statuses": [s.to_dict() for s in self.solver_statuses],
        }


class MultiphysicsTask(AggregateRoot):
    def __init__(
        self,
        model_id: str,
        coupling_type: CouplingType = CouplingType.AERO_STRUCTURAL,
        coupling_scheme: CouplingScheme = CouplingScheme.EXPLICIT_WEAK,
        convergence_criteria: ConvergenceCriteria | None = None,
        task_id: str | None = None,
    ) -> None:
        super().__init__(task_id)
        self.model_id: str = model_id
        self.coupling_type: CouplingType = coupling_type
        self.coupling_scheme: CouplingScheme = coupling_scheme
        self.convergence_criteria: ConvergenceCriteria = convergence_criteria or ConvergenceCriteria()
        self.participant_solvers: list[str] = self._resolve_solvers(coupling_type)
        self.status: MultiphysicsStatus = MultiphysicsStatus.QUEUED
        self.result_summary: MultiphysicsResultSummary | None = None
        self.error_message: str | None = None
        self.progress_percent: float = 0.0
        self.current_step: str = ""
        self.created_at: datetime = datetime.now(timezone.utc)
        self.updated_at: datetime = datetime.now(timezone.utc)
        self.completed_at: datetime | None = None

    @staticmethod
    def _resolve_solvers(coupling_type: CouplingType) -> list[str]:
        mapping: dict[CouplingType, list[str]] = {
            CouplingType.AERO_STRUCTURAL: ["CFD", "FEA"],
            CouplingType.THERMAL_STRUCTURAL: ["Thermal", "FEA"],
            CouplingType.AERO_THERMAL_STRUCTURAL: ["CFD", "Thermal", "FEA"],
        }
        return mapping.get(coupling_type, [])

    def start_running(self) -> None:
        if self.status != MultiphysicsStatus.QUEUED:
            raise ValueError(f"Cannot start from status {self.status}")
        self.status = MultiphysicsStatus.RUNNING
        self.progress_percent = 5.0
        self.current_step = "initializing_solvers"
        self.updated_at = datetime.now(timezone.utc)

    def start_converging(self) -> None:
        self.status = MultiphysicsStatus.CONVERGING
        self.current_step = "coupling_iteration"
        self.updated_at = datetime.now(timezone.utc)

    def complete(self, result: MultiphysicsResultSummary) -> None:
        if self.status not in (MultiphysicsStatus.RUNNING, MultiphysicsStatus.CONVERGING):
            raise ValueError(f"Cannot complete from status {self.status}")
        self.status = MultiphysicsStatus.COMPLETED
        self.result_summary = result
        self.progress_percent = 100.0
        self.current_step = "completed"
        self.completed_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        self.add_domain_event(DomainEvent(
            event_type="cae.analysis.completed",
            aggregate_id=self.id,
            payload={
                "task_id": self.id,
                "task_type": "multiphysics",
                "model_id": self.model_id,
                "result_summary": result.to_dict(),
            },
        ))

    def fail(self, error_message: str) -> None:
        self.status = MultiphysicsStatus.FAILED
        self.error_message = error_message
        self.current_step = "failed"
        self.updated_at = datetime.now(timezone.utc)

    def update_progress(self, percent: float, step: str) -> None:
        self.progress_percent = percent
        self.current_step = step
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "model_id": self.model_id,
            "coupling_type": self.coupling_type.value,
            "coupling_scheme": self.coupling_scheme.value,
            "convergence_criteria": self.convergence_criteria.to_dict(),
            "participant_solvers": self.participant_solvers,
            "status": self.status.value,
            "result_summary": self.result_summary.to_dict() if self.result_summary else None,
            "error_message": self.error_message,
            "progress_percent": self.progress_percent,
            "current_step": self.current_step,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }