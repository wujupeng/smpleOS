from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from aeroforge_common.domain.base import DomainEvent


class TopologyMethod(str, Enum):
    SIMP = "simp"
    LEVEL_SET = "level_set"
    BESO = "beso"
    HOMOGENIZATION = "homogenization"


class TopologyStatus(str, Enum):
    QUEUED = "queued"
    MESHING = "meshing"
    OPTIMIZING = "optimizing"
    POST_PROCESSING = "post_processing"
    COMPLETED = "completed"
    FAILED = "failed"


class LoadCaseType(str, Enum):
    TENSION = "tension"
    COMPRESSION = "compression"
    BENDING = "bending"
    TORSION = "torsion"
    COMBINED = "combined"


@dataclass
class LoadCase:
    name: str
    load_case_type: LoadCaseType = LoadCaseType.COMBINED
    force_x: float = 0.0
    force_y: float = 0.0
    force_z: float = 0.0
    moment_x: float = 0.0
    moment_y: float = 0.0
    moment_z: float = 0.0
    pressure: float = 0.0
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "load_case_type": self.load_case_type.value,
            "force_x": self.force_x,
            "force_y": self.force_y,
            "force_z": self.force_z,
            "moment_x": self.moment_x,
            "moment_y": self.moment_y,
            "moment_z": self.moment_z,
            "pressure": self.pressure,
            "description": self.description,
        }


@dataclass
class BoundaryCondition:
    name: str
    constrained_dofs: list[str] = field(default_factory=lambda: ["x", "y", "z"])
    region: str = ""
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "constrained_dofs": self.constrained_dofs,
            "region": self.region,
            "description": self.description,
        }


@dataclass
class DesignRegion:
    name: str
    volume_fraction: float = 0.3
    min_member_size: float = 2.0
    mesh_element_size: float = 1.0
    material_id: str = "aluminum_6061"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "volume_fraction": self.volume_fraction,
            "min_member_size": self.min_member_size,
            "mesh_element_size": self.mesh_element_size,
            "material_id": self.material_id,
        }


@dataclass
class TopologyResult:
    iteration_count: int = 0
    final_volume_fraction: float = 0.0
    compliance: float = 0.0
    max_stress: float = 0.0
    mass_reduction_pct: float = 0.0
    density_field: list[float] = field(default_factory=list)
    element_count: int = 0
    converged: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "iteration_count": self.iteration_count,
            "final_volume_fraction": self.final_volume_fraction,
            "compliance": self.compliance,
            "max_stress": self.max_stress,
            "mass_reduction_pct": self.mass_reduction_pct,
            "density_field_size": len(self.density_field),
            "element_count": self.element_count,
            "converged": self.converged,
        }


@dataclass
class TopologyOptimizationTask:
    id: str = field(default_factory=lambda: str(uuid4()))
    project_id: str = ""
    tenant_id: str = ""
    status: TopologyStatus = TopologyStatus.QUEUED
    method: TopologyMethod = TopologyMethod.SIMP
    design_regions: list[DesignRegion] = field(default_factory=list)
    load_cases: list[LoadCase] = field(default_factory=list)
    boundary_conditions: list[BoundaryCondition] = field(default_factory=list)
    max_iterations: int = 50
    convergence_tolerance: float = 1e-4
    penalty_factor: float = 3.0
    filter_radius: float = 1.5
    result: TopologyResult | None = None
    iteration_history: list[dict[str, Any]] = field(default_factory=list)
    error_message: str = ""
    created_by: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str = ""
    domain_events: list[DomainEvent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "tenant_id": self.tenant_id,
            "status": self.status.value,
            "method": self.method.value,
            "design_regions": [r.to_dict() for r in self.design_regions],
            "load_cases": [lc.to_dict() for lc in self.load_cases],
            "boundary_conditions": [bc.to_dict() for bc in self.boundary_conditions],
            "max_iterations": self.max_iterations,
            "convergence_tolerance": self.convergence_tolerance,
            "penalty_factor": self.penalty_factor,
            "filter_radius": self.filter_radius,
            "result": self.result.to_dict() if self.result else None,
            "iteration_history": self.iteration_history,
            "error_message": self.error_message,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }

    def start_meshing(self) -> None:
        if self.status != TopologyStatus.QUEUED:
            raise ValueError(f"Cannot start meshing in {self.status.value} status")
        self.status = TopologyStatus.MESHING

    def start_optimization(self) -> None:
        if self.status != TopologyStatus.MESHING:
            raise ValueError(f"Cannot start optimization in {self.status.value} status")
        self.status = TopologyStatus.OPTIMIZING

    def start_post_processing(self) -> None:
        if self.status != TopologyStatus.OPTIMIZING:
            raise ValueError(f"Cannot start post-processing in {self.status.value} status")
        self.status = TopologyStatus.POST_PROCESSING

    def complete(self, result: TopologyResult) -> None:
        self.status = TopologyStatus.COMPLETED
        self.result = result
        self.completed_at = datetime.now(timezone.utc).isoformat()
        self.add_domain_event(DomainEvent(
            event_type="topology_optimization.completed",
            aggregate_id=self.id,
            payload={"task_id": self.id, "mass_reduction_pct": result.mass_reduction_pct},
        ))

    def fail(self, error: str) -> None:
        self.status = TopologyStatus.FAILED
        self.error_message = error
        self.completed_at = datetime.now(timezone.utc).isoformat()

    def add_domain_event(self, event: DomainEvent) -> None:
        self.domain_events.append(event)