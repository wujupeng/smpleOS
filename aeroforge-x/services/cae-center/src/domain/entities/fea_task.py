from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from aeroforge_common.domain.base import AggregateRoot, DomainEvent


class FEAAnalysisType(str, Enum):
    STRENGTH = "strength"
    FATIGUE = "fatigue"
    DEFORMATION = "deformation"


class FEASolverType(str, Enum):
    FENICS = "FEniCS"
    CALCULIX = "CalculiX"


class FEAStatus(str, Enum):
    QUEUED = "queued"
    MESHING = "meshing"
    RUNNING = "running"
    POST_PROCESSING = "post_processing"
    COMPLETED = "completed"
    FAILED = "failed"


class LoadType(str, Enum):
    CONCENTRATED_FORCE = "concentrated_force"
    DISTRIBUTED_FORCE = "distributed_force"
    PRESSURE = "pressure"
    THERMAL = "thermal"
    INERTIAL = "inertial"


class BCType(str, Enum):
    FIXED = "fixed"
    SYMMETRY = "symmetry"
    CONTACT = "contact"


@dataclass
class LoadCase:
    name: str
    load_type: LoadType
    region: str
    values: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "load_type": self.load_type.value,
            "region": self.region,
            "values": self.values,
        }


@dataclass
class BoundaryCondition:
    name: str
    bc_type: BCType
    region: str
    values: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "bc_type": self.bc_type.value,
            "region": self.region,
            "values": self.values,
        }


@dataclass
class MaterialProperties:
    name: str
    elastic_modulus_pa: float = 200e9
    poisson_ratio: float = 0.3
    density_kg_m3: float = 7850.0
    thermal_expansion_coeff: float = 12e-6
    yield_strength_pa: float = 250e6
    ultimate_strength_pa: float = 400e6

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "elastic_modulus_pa": self.elastic_modulus_pa,
            "poisson_ratio": self.poisson_ratio,
            "density_kg_m3": self.density_kg_m3,
            "thermal_expansion_coeff": self.thermal_expansion_coeff,
            "yield_strength_pa": self.yield_strength_pa,
            "ultimate_strength_pa": self.ultimate_strength_pa,
        }


@dataclass
class FEAResultSummary:
    max_stress_pa: float = 0.0
    max_deformation_m: float = 0.0
    safety_factor: float = 0.0
    fatigue_life_cycles: float = 0.0
    von_mises_max_pa: float = 0.0
    principal_stress_max_pa: float = 0.0
    convergence_status: str = "not_converged"

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_stress_pa": self.max_stress_pa,
            "max_deformation_m": self.max_deformation_m,
            "safety_factor": self.safety_factor,
            "fatigue_life_cycles": self.fatigue_life_cycles,
            "von_mises_max_pa": self.von_mises_max_pa,
            "principal_stress_max_pa": self.principal_stress_max_pa,
            "convergence_status": self.convergence_status,
        }


class FEATask(AggregateRoot):
    def __init__(
        self,
        model_id: str,
        analysis_type: FEAAnalysisType = FEAAnalysisType.STRENGTH,
        solver_type: FEASolverType = FEASolverType.FENICS,
        mesh_task_id: str | None = None,
        task_id: str | None = None,
    ) -> None:
        super().__init__(task_id)
        self.model_id: str = model_id
        self.analysis_type: FEAAnalysisType = analysis_type
        self.solver_type: FEASolverType = solver_type
        self.mesh_task_id: str | None = mesh_task_id
        self.status: FEAStatus = FEAStatus.QUEUED
        self.load_cases: list[LoadCase] = []
        self.boundary_conditions: list[BoundaryCondition] = []
        self.material_properties: MaterialProperties | None = None
        self.result_summary: FEAResultSummary | None = None
        self.error_message: str | None = None
        self.progress_percent: float = 0.0
        self.current_step: str = ""
        self.created_at: datetime = datetime.now(timezone.utc)
        self.updated_at: datetime = datetime.now(timezone.utc)
        self.completed_at: datetime | None = None

    def add_load_case(self, load_case: LoadCase) -> None:
        self.load_cases.append(load_case)

    def add_boundary_condition(self, bc: BoundaryCondition) -> None:
        self.boundary_conditions.append(bc)

    def set_material(self, material: MaterialProperties) -> None:
        self.material_properties = material

    def start_meshing(self) -> None:
        if self.status != FEAStatus.QUEUED:
            raise ValueError(f"Cannot start meshing from status {self.status}")
        self.status = FEAStatus.MESHING
        self.progress_percent = 5.0
        self.current_step = "meshing"
        self.updated_at = datetime.now(timezone.utc)

    def start_running(self) -> None:
        if self.status != FEAStatus.MESHING:
            raise ValueError(f"Cannot start running from status {self.status}")
        self.status = FEAStatus.RUNNING
        self.progress_percent = 30.0
        self.current_step = "running_solver"
        self.updated_at = datetime.now(timezone.utc)

    def start_post_processing(self) -> None:
        if self.status != FEAStatus.RUNNING:
            raise ValueError(f"Cannot start post-processing from status {self.status}")
        self.status = FEAStatus.POST_PROCESSING
        self.progress_percent = 70.0
        self.current_step = "post_processing"
        self.updated_at = datetime.now(timezone.utc)

    def complete(self, result: FEAResultSummary) -> None:
        if self.status != FEAStatus.POST_PROCESSING:
            raise ValueError(f"Cannot complete from status {self.status}")
        self.status = FEAStatus.COMPLETED
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
                "task_type": "fea",
                "model_id": self.model_id,
                "result_summary": result.to_dict(),
            },
        ))

    def fail(self, error_message: str) -> None:
        self.status = FEAStatus.FAILED
        self.error_message = error_message
        self.current_step = "failed"
        self.updated_at = datetime.now(timezone.utc)
        self.add_domain_event(DomainEvent(
            event_type="cae.analysis.failed",
            aggregate_id=self.id,
            payload={
                "task_id": self.id,
                "task_type": "fea",
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
            "mesh_task_id": self.mesh_task_id,
            "status": self.status.value,
            "load_cases": [lc.to_dict() for lc in self.load_cases],
            "boundary_conditions": [bc.to_dict() for bc in self.boundary_conditions],
            "material_properties": self.material_properties.to_dict() if self.material_properties else None,
            "result_summary": self.result_summary.to_dict() if self.result_summary else None,
            "error_message": self.error_message,
            "progress_percent": self.progress_percent,
            "current_step": self.current_step,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }