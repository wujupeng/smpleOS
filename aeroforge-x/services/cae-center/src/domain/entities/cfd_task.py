from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from aeroforge_common.domain.base import AggregateRoot, DomainEvent


class CFDAnalysisType(str, Enum):
    STEADY = "steady"
    UNSTEADY = "unsteady"


class CFDSolverType(str, Enum):
    SIMPLE_FOAM = "simpleFoam"
    RHO_SIMPLE_FOAM = "rhoSimpleFoam"
    PIMPLE_FOAM = "pimpleFoam"


class CFDStatus(str, Enum):
    QUEUED = "queued"
    MESHING = "meshing"
    RUNNING = "running"
    POST_PROCESSING = "post_processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TurbulenceModel(str, Enum):
    K_OMEGA_SST = "kOmegaSST"
    K_EPSILON = "kEpsilon"
    SPALART_ALLMARAS = "SpalartAllmaras"


@dataclass
class FlightConditions:
    altitude_m: float = 0.0
    mach_number: float = 0.0
    reynolds_number: float = 0.0
    angle_of_attack_deg: float = 0.0
    sideslip_angle_deg: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "altitude_m": self.altitude_m,
            "mach_number": self.mach_number,
            "reynolds_number": self.reynolds_number,
            "angle_of_attack_deg": self.angle_of_attack_deg,
            "sideslip_angle_deg": self.sideslip_angle_deg,
        }


@dataclass
class CFDResultSummary:
    lift_coefficient: float = 0.0
    drag_coefficient: float = 0.0
    moment_coefficient: float = 0.0
    convergence_status: str = "not_converged"
    residual_final: dict[str, float] = field(default_factory=dict)
    lift_to_drag_ratio: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "lift_coefficient": self.lift_coefficient,
            "drag_coefficient": self.drag_coefficient,
            "moment_coefficient": self.moment_coefficient,
            "convergence_status": self.convergence_status,
            "residual_final": self.residual_final,
            "lift_to_drag_ratio": self.lift_to_drag_ratio,
        }


class CFDTask(AggregateRoot):
    def __init__(
        self,
        model_id: str,
        analysis_type: CFDAnalysisType = CFDAnalysisType.STEADY,
        solver_type: CFDSolverType = CFDSolverType.SIMPLE_FOAM,
        turbulence_model: TurbulenceModel = TurbulenceModel.K_OMEGA_SST,
        flight_conditions: FlightConditions | None = None,
        mesh_task_id: str | None = None,
        task_id: str | None = None,
    ) -> None:
        super().__init__(task_id)
        self.model_id: str = model_id
        self.analysis_type: CFDAnalysisType = analysis_type
        self.solver_type: CFDSolverType = solver_type
        self.turbulence_model: TurbulenceModel = turbulence_model
        self.flight_conditions: FlightConditions = flight_conditions or FlightConditions()
        self.mesh_task_id: str | None = mesh_task_id
        self.status: CFDStatus = CFDStatus.QUEUED
        self.result_summary: CFDResultSummary | None = None
        self.case_dir: str = ""
        self.error_message: str | None = None
        self.progress_percent: float = 0.0
        self.current_step: str = ""
        self.created_at: datetime = datetime.now(timezone.utc)
        self.updated_at: datetime = datetime.now(timezone.utc)
        self.completed_at: datetime | None = None
        self.openfoam_params: dict[str, Any] = field(default_factory=dict)

    def start_meshing(self) -> None:
        if self.status != CFDStatus.QUEUED:
            raise ValueError(f"Cannot start meshing from status {self.status}")
        self.status = CFDStatus.MESHING
        self.progress_percent = 5.0
        self.current_step = "meshing"
        self.updated_at = datetime.now(timezone.utc)

    def start_running(self) -> None:
        if self.status != CFDStatus.MESHING:
            raise ValueError(f"Cannot start running from status {self.status}")
        self.status = CFDStatus.RUNNING
        self.progress_percent = 30.0
        self.current_step = "running_solver"
        self.updated_at = datetime.now(timezone.utc)

    def start_post_processing(self) -> None:
        if self.status != CFDStatus.RUNNING:
            raise ValueError(f"Cannot start post-processing from status {self.status}")
        self.status = CFDStatus.POST_PROCESSING
        self.progress_percent = 70.0
        self.current_step = "post_processing"
        self.updated_at = datetime.now(timezone.utc)

    def complete(self, result: CFDResultSummary) -> None:
        if self.status != CFDStatus.POST_PROCESSING:
            raise ValueError(f"Cannot complete from status {self.status}")
        self.status = CFDStatus.COMPLETED
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
                "task_type": "cfd",
                "model_id": self.model_id,
                "result_summary": result.to_dict(),
            },
        ))

    def fail(self, error_message: str) -> None:
        self.status = CFDStatus.FAILED
        self.error_message = error_message
        self.current_step = "failed"
        self.updated_at = datetime.now(timezone.utc)
        self.add_domain_event(DomainEvent(
            event_type="cae.analysis.failed",
            aggregate_id=self.id,
            payload={
                "task_id": self.id,
                "task_type": "cfd",
                "model_id": self.model_id,
                "error": error_message,
            },
        ))

    def update_progress(self, percent: float, step: str) -> None:
        self.progress_percent = percent
        self.current_step = step
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "model_id": self.model_id,
            "analysis_type": self.analysis_type.value,
            "solver_type": self.solver_type.value,
            "turbulence_model": self.turbulence_model.value,
            "flight_conditions": self.flight_conditions.to_dict(),
            "mesh_task_id": self.mesh_task_id,
            "status": self.status.value,
            "result_summary": self.result_summary.to_dict() if self.result_summary else None,
            "case_dir": self.case_dir,
            "error_message": self.error_message,
            "progress_percent": self.progress_percent,
            "current_step": self.current_step,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }