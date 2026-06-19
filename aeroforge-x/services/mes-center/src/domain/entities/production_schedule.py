from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from aeroforge_common.domain.base import DomainEvent


class ScheduleStatus(str, Enum):
    DRAFT = "draft"
    OPTIMIZED = "optimized"
    CONFIRMED = "confirmed"
    EXECUTING = "executing"


class ObjectiveFunction(str, Enum):
    MIN_MAKESPAN = "min_makespan"
    MIN_COST = "min_cost"
    MAX_RESOURCE_UTIL = "max_resource_util"


class ConstraintType(str, Enum):
    CAPACITY = "capacity"
    PRECEDENCE = "precedence"
    RESOURCE = "resource"
    DUE_DATE = "due_date"
    MATERIAL = "material"


class ConstraintPriority(str, Enum):
    HARD = "hard"
    SOFT = "soft"


@dataclass
class ScheduleConstraint:
    id: str = field(default_factory=lambda: str(uuid4()))
    constraint_type: ConstraintType = ConstraintType.CAPACITY
    constraint_expression: str = ""
    priority: ConstraintPriority = ConstraintPriority.HARD
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "constraint_type": self.constraint_type.value,
            "constraint_expression": self.constraint_expression,
            "priority": self.priority.value,
            "description": self.description,
        }


@dataclass
class ScheduledOperation:
    work_order_id: str = ""
    operation_name: str = ""
    workstation: str = ""
    start_time: int = 0
    end_time: int = 0
    duration_hours: float = 0.0
    required_skills: list[str] = field(default_factory=list)
    required_materials: list[str] = field(default_factory=list)
    predecessor_ops: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "work_order_id": self.work_order_id,
            "operation_name": self.operation_name,
            "workstation": self.workstation,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_hours": self.duration_hours,
            "required_skills": self.required_skills,
            "required_materials": self.required_materials,
            "predecessor_ops": self.predecessor_ops,
        }


@dataclass
class WorkOrderSchedule:
    work_order_id: str = ""
    work_order_code: str = ""
    priority: int = 0
    due_date: str = ""
    operations: list[ScheduledOperation] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "work_order_id": self.work_order_id,
            "work_order_code": self.work_order_code,
            "priority": self.priority,
            "due_date": self.due_date,
            "operations": [op.to_dict() for op in self.operations],
        }


@dataclass
class ResourceInfo:
    resource_id: str = ""
    resource_name: str = ""
    resource_type: str = "workstation"
    capacity: int = 1
    skills: list[str] = field(default_factory=list)
    available_from: int = 0
    available_to: int = 240

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "resource_name": self.resource_name,
            "resource_type": self.resource_type,
            "capacity": self.capacity,
            "skills": self.skills,
            "available_from": self.available_from,
            "available_to": self.available_to,
        }


@dataclass
class ProductionSchedule:
    id: str = field(default_factory=lambda: str(uuid4()))
    tenant_id: str = ""
    project_id: str = ""
    name: str = ""
    status: ScheduleStatus = ScheduleStatus.DRAFT
    schedule_horizon_start: str = ""
    schedule_horizon_end: str = ""
    work_orders: list[WorkOrderSchedule] = field(default_factory=list)
    resources: list[ResourceInfo] = field(default_factory=list)
    constraints: list[ScheduleConstraint] = field(default_factory=list)
    objective_function: ObjectiveFunction = ObjectiveFunction.MIN_MAKESPAN
    gantt_data: list[dict[str, Any]] = field(default_factory=list)
    resource_utilization: dict[str, float] = field(default_factory=dict)
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    makespan_hours: float = 0.0
    total_cost: float = 0.0
    created_by: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    domain_events: list[DomainEvent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "name": self.name,
            "status": self.status.value,
            "schedule_horizon_start": self.schedule_horizon_start,
            "schedule_horizon_end": self.schedule_horizon_end,
            "work_orders": [wo.to_dict() for wo in self.work_orders],
            "resources": [r.to_dict() for r in self.resources],
            "constraints": [c.to_dict() for c in self.constraints],
            "objective_function": self.objective_function.value,
            "gantt_data": self.gantt_data,
            "resource_utilization": self.resource_utilization,
            "conflicts": self.conflicts,
            "makespan_hours": self.makespan_hours,
            "total_cost": self.total_cost,
            "created_by": self.created_by,
            "created_at": self.created_at,
        }

    def add_domain_event(self, event: DomainEvent) -> None:
        self.domain_events.append(event)