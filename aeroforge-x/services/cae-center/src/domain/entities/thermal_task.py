from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from aeroforge_common.domain.base import AggregateRoot, DomainEvent


class ThermalAnalysisType(str, Enum):
    STEADY_STATE = "steady_state"
    TRANSIENT = "transient"


class ThermalStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class HeatSource:
    name: str
    source_type: str = "volumetric"
    region: str = ""
    power_watts: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "source_type": self.source_type,
                "region": self.region, "power_watts": self.power_watts}


@dataclass
class ThermalBoundaryCondition:
    name: str
    bc_type: str = "convection"
    region: str = ""
    h_coeff: float = 25.0
    ambient_temp_c: float = 25.0
    emissivity: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "bc_type": self.bc_type, "region": self.region,
                "h_coeff": self.h_coeff, "ambient_temp_c": self.ambient_temp_c,
                "emissivity": self.emissivity}


@dataclass
class CoolantParams:
    coolant_type: str = "water"
    flow_rate_lpm: float = 5.0
    inlet_temp_c: float = 20.0

    def to_dict(self) -> dict[str, Any]:
        return {"coolant_type": self.coolant_type, "flow_rate_lpm": self.flow_rate_lpm,
                "inlet_temp_c": self.inlet_temp_c}


@dataclass
class ThermalResultSummary:
    max_temperature_c: float = 0.0
    min_temperature_c: float = 0.0
    avg_temperature_c: float = 0.0
    max_heat_flux_w_m2: float = 0.0
    max_thermal_gradient_c_m: float = 0.0
    overheated_regions: list[dict[str, Any]] = field(default_factory=list)
    thermal_management_suggestions: list[str] = field(default_factory=list)
    convergence_status: str = "converged"

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_temperature_c": self.max_temperature_c,
            "min_temperature_c": self.min_temperature_c,
            "avg_temperature_c": self.avg_temperature_c,
            "max_heat_flux_w_m2": self.max_heat_flux_w_m2,
            "max_thermal_gradient_c_m": self.max_thermal_gradient_c_m,
            "overheated_regions": self.overheated_regions,
            "thermal_management_suggestions": self.thermal_management_suggestions,
            "convergence_status": self.convergence_status,
        }


class ThermalTask(AggregateRoot):
    def __init__(
        self,
        model_id: str,
        analysis_type: ThermalAnalysisType = ThermalAnalysisType.STEADY_STATE,
        mesh_task_id: str | None = None,
        task_id: str | None = None,
    ) -> None:
        super().__init__(task_id)
        self.model_id: str = model_id
        self.analysis_type: ThermalAnalysisType = analysis_type
        self.mesh_task_id: str | None = mesh_task_id
        self.heat_sources: list[HeatSource] = []
        self.thermal_boundary_conditions: list[ThermalBoundaryCondition] = []
        self.coolant: CoolantParams | None = None
        self.status: ThermalStatus = ThermalStatus.QUEUED
        self.result_summary: ThermalResultSummary | None = None
        self.error_message: str | None = None
        self.progress_percent: float = 0.0
        self.current_step: str = ""
        self.created_at: datetime = datetime.now(timezone.utc)
        self.updated_at: datetime = datetime.now(timezone.utc)
        self.completed_at: datetime | None = None

    def add_heat_source(self, hs: HeatSource) -> None:
        self.heat_sources.append(hs)

    def add_thermal_bc(self, bc: ThermalBoundaryCondition) -> None:
        self.thermal_boundary_conditions.append(bc)

    def set_coolant(self, coolant: CoolantParams) -> None:
        self.coolant = coolant

    def start_running(self) -> None:
        if self.status != ThermalStatus.QUEUED:
            raise ValueError(f"Cannot start from status {self.status}")
        self.status = ThermalStatus.RUNNING
        self.progress_percent = 10.0
        self.current_step = "preparing_thermal_problem"
        self.updated_at = datetime.now(timezone.utc)

    def complete(self, result: ThermalResultSummary) -> None:
        if self.status != ThermalStatus.RUNNING:
            raise ValueError(f"Cannot complete from status {self.status}")
        self.status = ThermalStatus.COMPLETED
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
                "task_type": "thermal",
                "model_id": self.model_id,
                "result_summary": result.to_dict(),
            },
        ))

    def fail(self, error_message: str) -> None:
        self.status = ThermalStatus.FAILED
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
            "analysis_type": self.analysis_type.value,
            "mesh_task_id": self.mesh_task_id,
            "heat_sources": [hs.to_dict() for hs in self.heat_sources],
            "thermal_boundary_conditions": [bc.to_dict() for bc in self.thermal_boundary_conditions],
            "coolant": self.coolant.to_dict() if self.coolant else None,
            "status": self.status.value,
            "result_summary": self.result_summary.to_dict() if self.result_summary else None,
            "error_message": self.error_message,
            "progress_percent": self.progress_percent,
            "current_step": self.current_step,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }