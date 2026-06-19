from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from aeroforge_common.domain.base import AggregateRoot


class OptimizationType(str, Enum):
    CYCLE_TIME = "cycle_time"
    QUALITY = "quality"
    COST = "cost"
    ENERGY = "energy"


class ValidationStatus(str, Enum):
    SIMULATED = "simulated"
    VALIDATED = "validated"
    REJECTED = "rejected"


class OptimizationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ProcessParameter:
    name: str
    value: float
    unit: str = ""
    min_bound: float = 0.0
    max_bound: float = float("inf")

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "min_bound": self.min_bound,
            "max_bound": self.max_bound,
        }


@dataclass
class ImprovementMetrics:
    time_reduction_pct: float = 0.0
    quality_improvement_pct: float = 0.0
    cost_reduction_pct: float = 0.0
    energy_reduction_pct: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "time_reduction_pct": round(self.time_reduction_pct, 2),
            "quality_improvement_pct": round(self.quality_improvement_pct, 2),
            "cost_reduction_pct": round(self.cost_reduction_pct, 2),
            "energy_reduction_pct": round(self.energy_reduction_pct, 2),
        }


@dataclass
class BottleneckInfo:
    station_id: str
    station_name: str
    utilization_rate: float
    avg_wait_time_minutes: float
    avg_process_time_minutes: float
    is_critical_path: bool = False
    bottleneck_severity: str = "medium"

    def to_dict(self) -> dict[str, Any]:
        return {
            "station_id": self.station_id,
            "station_name": self.station_name,
            "utilization_rate": round(self.utilization_rate, 4),
            "avg_wait_time_minutes": round(self.avg_wait_time_minutes, 1),
            "avg_process_time_minutes": round(self.avg_process_time_minutes, 1),
            "is_critical_path": self.is_critical_path,
            "bottleneck_severity": self.bottleneck_severity,
        }


@dataclass
class SimulationResult:
    schedule_impact: dict[str, Any] = field(default_factory=dict)
    capacity_change_pct: float = 0.0
    delivery_impact_days: float = 0.0
    risk_assessment: str = "low"
    feasible: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "schedule_impact": self.schedule_impact,
            "capacity_change_pct": round(self.capacity_change_pct, 2),
            "delivery_impact_days": round(self.delivery_impact_days, 1),
            "risk_assessment": self.risk_assessment,
            "feasible": self.feasible,
        }


@dataclass
class ValidationResult:
    sample_size: int = 0
    pass_rate_before: float = 0.0
    pass_rate_after: float = 0.0
    statistical_significance: float = 0.0
    is_significant: bool = False
    validated_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "sample_size": self.sample_size,
            "pass_rate_before": round(self.pass_rate_before, 4),
            "pass_rate_after": round(self.pass_rate_after, 4),
            "statistical_significance": round(self.statistical_significance, 4),
            "is_significant": self.is_significant,
            "validated_at": self.validated_at.isoformat() if self.validated_at else None,
        }


class ProcessOptimization(AggregateRoot):
    def __init__(
        self,
        tenant_id: str,
        project_id: str,
        process_route_id: str,
        optimization_type: OptimizationType,
    ) -> None:
        super().__init__()
        self.tenant_id = tenant_id
        self.project_id = project_id
        self.process_route_id = process_route_id
        self.optimization_type = optimization_type
        self.current_process_params: list[ProcessParameter] = []
        self.optimized_process_params: list[ProcessParameter] = []
        self.improvement_metrics = ImprovementMetrics()
        self.bottleneck_analysis: list[BottleneckInfo] = []
        self.simulation_result: SimulationResult | None = None
        self.validation_result: ValidationResult | None = None
        self.validation_status = ValidationStatus.SIMULATED
        self.status = OptimizationStatus.PENDING
        self.deployed_at: datetime | None = None
        self.created_at = datetime.now(timezone.utc)

    def set_current_params(self, params: list[ProcessParameter]) -> None:
        self.current_process_params = params

    def set_optimized_params(self, params: list[ProcessParameter]) -> None:
        self.optimized_process_params = params

    def set_improvement_metrics(self, metrics: ImprovementMetrics) -> None:
        self.improvement_metrics = metrics

    def set_bottleneck_analysis(self, bottlenecks: list[BottleneckInfo]) -> None:
        self.bottleneck_analysis = bottlenecks

    def set_simulation_result(self, result: SimulationResult) -> None:
        self.simulation_result = result

    def set_validation_result(self, result: ValidationResult) -> None:
        self.validation_result = result
        if result.is_significant:
            self.validation_status = ValidationStatus.VALIDATED
        else:
            self.validation_status = ValidationStatus.REJECTED

    def mark_deployed(self) -> None:
        self.deployed_at = datetime.now(timezone.utc)
        self.status = OptimizationStatus.COMPLETED

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "process_route_id": self.process_route_id,
            "optimization_type": self.optimization_type.value,
            "status": self.status.value,
            "validation_status": self.validation_status.value,
            "improvement_metrics": self.improvement_metrics.to_dict(),
            "created_at": self.created_at.isoformat(),
            "deployed_at": self.deployed_at.isoformat() if self.deployed_at else None,
        }

    def to_detail_dict(self) -> dict[str, Any]:
        base = self.to_dict()
        base.update({
            "current_process_params": [p.to_dict() for p in self.current_process_params],
            "optimized_process_params": [p.to_dict() for p in self.optimized_process_params],
            "bottleneck_analysis": [b.to_dict() for b in self.bottleneck_analysis],
            "simulation_result": self.simulation_result.to_dict() if self.simulation_result else None,
            "validation_result": self.validation_result.to_dict() if self.validation_result else None,
        })
        return base