from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from aeroforge_common.domain.base import AggregateRoot, DomainEvent


class CustomFEAStatus(str, Enum):
    QUEUED = "queued"
    PARSING_UFL = "parsing_ufl"
    SOLVING = "solving"
    POST_PROCESSING = "post_processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FatigueAnalysisStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING_SPECTRUM = "processing_spectrum"
    COMPUTING_DAMAGE = "computing_damage"
    COMPLETED = "completed"
    FAILED = "failed"


class BucklingAnalysisStatus(str, Enum):
    QUEUED = "queued"
    SOLVING = "solving"
    COMPLETED = "completed"
    FAILED = "failed"


class MeanStressCorrection(str, Enum):
    NONE = "none"
    GOODMAN = "goodman"
    GERBER = "gerber"


@dataclass
class UFLDefinition:
    filename: str
    content: str
    boundary_conditions: list[dict[str, Any]] = field(default_factory=list)
    material_props: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "content": self.content,
            "boundary_conditions": self.boundary_conditions,
            "material_props": self.material_props,
        }


@dataclass
class FEASolutionField:
    name: str
    values: list[float] = field(default_factory=list)
    min_val: float = 0.0
    max_val: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "num_values": len(self.values),
            "min": self.min_val,
            "max": self.max_val,
        }


class CustomFEATask(AggregateRoot):
    def __init__(
        self,
        model_id: str,
        project_id: str = "default",
        tenant_id: str = "default",
        ufl_definition: UFLDefinition | None = None,
        task_id: str | None = None,
    ) -> None:
        super().__init__(task_id)
        self.model_id = model_id
        self.project_id = project_id
        self.tenant_id = tenant_id
        self.ufl_definition = ufl_definition
        self.status = CustomFEAStatus.QUEUED
        self.solution_fields: list[FEASolutionField] = []
        self.error_message: str | None = None
        self.solve_time_seconds: float = 0.0
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def complete(self, fields: list[FEASolutionField], solve_time: float) -> None:
        self.status = CustomFEAStatus.COMPLETED
        self.solution_fields = fields
        self.solve_time_seconds = solve_time
        self.updated_at = datetime.now(timezone.utc)
        self.add_domain_event(DomainEvent(
            event_type="cae.custom_fea.completed",
            aggregate_id=self.id,
            payload={"task_id": self.id, "model_id": self.model_id},
        ))

    def fail(self, error: str) -> None:
        self.status = CustomFEAStatus.FAILED
        self.error_message = error
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "model_id": self.model_id,
            "project_id": self.project_id,
            "tenant_id": self.tenant_id,
            "ufl_definition": self.ufl_definition.to_dict() if self.ufl_definition else None,
            "status": self.status.value,
            "solution_fields": [f.to_dict() for f in self.solution_fields],
            "error_message": self.error_message,
            "solve_time_seconds": self.solve_time_seconds,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class RainflowCycle:
    range_val: float
    mean: float
    count: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {"range": self.range_val, "mean": self.mean, "count": self.count}


@dataclass
class SNCurvePoint:
    cycles: float
    stress_amplitude: float

    def to_dict(self) -> dict[str, Any]:
        return {"cycles": self.cycles, "stress_amplitude": self.stress_amplitude}


@dataclass
class FatigueDamageResult:
    element_id: int
    damage: float
    life_cycles: float
    critical: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "element_id": self.element_id,
            "damage": self.damage,
            "life_cycles": self.life_cycles,
            "critical": self.critical,
        }


class FatigueAnalysisTask(AggregateRoot):
    def __init__(
        self,
        model_id: str,
        project_id: str = "default",
        tenant_id: str = "default",
        load_spectrum: list[float] | None = None,
        sn_curve: list[dict[str, float]] | None = None,
        mean_stress_correction: MeanStressCorrection = MeanStressCorrection.GOODMAN,
        endurance_limit: float = 1e7,
        task_id: str | None = None,
    ) -> None:
        super().__init__(task_id)
        self.model_id = model_id
        self.project_id = project_id
        self.tenant_id = tenant_id
        self.load_spectrum = load_spectrum or []
        self.sn_curve = sn_curve or []
        self.mean_stress_correction = mean_stress_correction
        self.endurance_limit = endurance_limit
        self.status = FatigueAnalysisStatus.QUEUED
        self.rainflow_cycles: list[RainflowCycle] = []
        self.damage_results: list[FatigueDamageResult] = []
        self.total_damage: float = 0.0
        self.min_life_cycles: float = float("inf")
        self.error_message: str | None = None
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def complete(self, cycles: list[RainflowCycle], damage: list[FatigueDamageResult]) -> None:
        self.status = FatigueAnalysisStatus.COMPLETED
        self.rainflow_cycles = cycles
        self.damage_results = damage
        self.total_damage = sum(d.damage for d in damage)
        self.min_life_cycles = min((d.life_cycles for d in damage), default=float("inf"))
        self.updated_at = datetime.now(timezone.utc)
        self.add_domain_event(DomainEvent(
            event_type="cae.fatigue_analysis.completed",
            aggregate_id=self.id,
            payload={"task_id": self.id, "total_damage": self.total_damage},
        ))

    def fail(self, error: str) -> None:
        self.status = FatigueAnalysisStatus.FAILED
        self.error_message = error
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "model_id": self.model_id,
            "project_id": self.project_id,
            "tenant_id": self.tenant_id,
            "mean_stress_correction": self.mean_stress_correction.value,
            "endurance_limit": self.endurance_limit,
            "status": self.status.value,
            "rainflow_cycles": [rc.to_dict() for rc in self.rainflow_cycles],
            "damage_results": [dr.to_dict() for dr in self.damage_results],
            "total_damage": self.total_damage,
            "min_life_cycles": self.min_life_cycles,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class BucklingMode:
    mode_number: int
    critical_load_factor: float
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode_number": self.mode_number,
            "critical_load_factor": self.critical_load_factor,
            "description": self.description,
        }


class BucklingAnalysisTask(AggregateRoot):
    def __init__(
        self,
        model_id: str,
        project_id: str = "default",
        tenant_id: str = "default",
        num_modes: int = 5,
        task_id: str | None = None,
    ) -> None:
        super().__init__(task_id)
        self.model_id = model_id
        self.project_id = project_id
        self.tenant_id = tenant_id
        self.num_modes = num_modes
        self.status = BucklingAnalysisStatus.QUEUED
        self.buckling_modes: list[BucklingMode] = []
        self.critical_load_factor: float = 0.0
        self.error_message: str | None = None
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def complete(self, modes: list[BucklingMode]) -> None:
        self.status = BucklingAnalysisStatus.COMPLETED
        self.buckling_modes = modes
        self.critical_load_factor = modes[0].critical_load_factor if modes else 0.0
        self.updated_at = datetime.now(timezone.utc)
        self.add_domain_event(DomainEvent(
            event_type="cae.buckling_analysis.completed",
            aggregate_id=self.id,
            payload={"task_id": self.id, "critical_load_factor": self.critical_load_factor},
        ))

    def fail(self, error: str) -> None:
        self.status = BucklingAnalysisStatus.FAILED
        self.error_message = error
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "model_id": self.model_id,
            "project_id": self.project_id,
            "tenant_id": self.tenant_id,
            "num_modes": self.num_modes,
            "status": self.status.value,
            "buckling_modes": [bm.to_dict() for bm in self.buckling_modes],
            "critical_load_factor": self.critical_load_factor,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }