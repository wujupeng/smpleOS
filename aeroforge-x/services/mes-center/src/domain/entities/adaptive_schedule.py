from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from aeroforge_common.domain.base import AggregateRoot, DomainEvent


class AdaptationTriggerType(str, Enum):
    STATION_FAILURE = "station_failure"
    STATION_RECOVERY = "station_recovery"
    MATERIAL_DELAY = "material_delay"
    URGENT_INSERT = "urgent_insert"
    QUALITY_ANOMALY = "quality_anomaly"
    PERSONNEL_ABSENCE = "personnel_absence"
    DEADLINE_CHANGE = "deadline_change"


class AdaptationStatus(str, Enum):
    PENDING = "pending"
    APPLIED = "applied"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"


class ScheduleStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"


@dataclass
class AdaptationTrigger:
    trigger_id: str
    trigger_type: AdaptationTriggerType
    description: str
    affected_operations: list[str] = field(default_factory=list)
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    severity: str = "medium"

    def to_dict(self) -> dict[str, Any]:
        return {
            "trigger_id": self.trigger_id,
            "trigger_type": self.trigger_type.value,
            "description": self.description,
            "affected_operations": self.affected_operations,
            "detected_at": self.detected_at.isoformat(),
            "severity": self.severity,
        }


@dataclass
class AdaptationRecord:
    record_id: str
    trigger: AdaptationTrigger
    original_schedule: dict[str, Any]
    adjusted_schedule: dict[str, Any]
    impact_assessment: dict[str, Any]
    status: AdaptationStatus = AdaptationStatus.PENDING
    approved_by: str = ""
    applied_at: datetime | None = None
    cost_impact: float = 0.0
    delay_impact_hours: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "trigger": self.trigger.to_dict(),
            "status": self.status.value,
            "cost_impact": self.cost_impact,
            "delay_impact_hours": self.delay_impact_hours,
            "impact_assessment": self.impact_assessment,
            "approved_by": self.approved_by,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
        }


@dataclass
class PerformanceMetrics:
    on_time_rate: float = 0.0
    utilization_rate: float = 0.0
    adaptation_count: int = 0
    avg_adjustment_time_minutes: float = 0.0
    total_delay_hours: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "on_time_rate": round(self.on_time_rate, 3),
            "utilization_rate": round(self.utilization_rate, 3),
            "adaptation_count": self.adaptation_count,
            "avg_adjustment_time_minutes": round(self.avg_adjustment_time_minutes, 1),
            "total_delay_hours": round(self.total_delay_hours, 1),
        }


class AdaptiveSchedule(AggregateRoot):
    def __init__(
        self,
        tenant_id: str,
        project_id: str,
        name: str,
        base_schedule: dict[str, Any] | None = None,
    ) -> None:
        super().__init__()
        self.tenant_id = tenant_id
        self.project_id = project_id
        self.name = name
        self.base_schedule = base_schedule or {}
        self.current_schedule = dict(self.base_schedule)
        self.adaptation_triggers: list[AdaptationTrigger] = []
        self.adaptation_history: list[AdaptationRecord] = []
        self.performance_metrics = PerformanceMetrics()
        self.status = ScheduleStatus.ACTIVE
        self.created_at = datetime.now(timezone.utc)

    def add_trigger(self, trigger: AdaptationTrigger) -> None:
        self.adaptation_triggers.append(trigger)

    def add_adaptation(self, record: AdaptationRecord) -> None:
        self.adaptation_history.append(record)
        if record.status == AdaptationStatus.APPLIED:
            self.current_schedule = record.adjusted_schedule
            self.performance_metrics.adaptation_count += 1

    def update_metrics(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            if hasattr(self.performance_metrics, key):
                setattr(self.performance_metrics, key, value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "name": self.name,
            "status": self.status.value,
            "performance_metrics": self.performance_metrics.to_dict(),
            "triggers_count": len(self.adaptation_triggers),
            "adaptations_count": len(self.adaptation_history),
            "created_at": self.created_at.isoformat(),
        }

    def to_detail_dict(self) -> dict[str, Any]:
        base = self.to_dict()
        base.update({
            "base_schedule": self.base_schedule,
            "current_schedule": self.current_schedule,
            "adaptation_triggers": [t.to_dict() for t in self.adaptation_triggers],
            "adaptation_history": [r.to_dict() for r in self.adaptation_history],
        })
        return base