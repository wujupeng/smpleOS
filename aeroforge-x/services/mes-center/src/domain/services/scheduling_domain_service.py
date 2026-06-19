from __future__ import annotations

import logging
from typing import Any

from aeroforge_common.domain.base import DomainEvent

from .entities.production_schedule import (
    ProductionSchedule, ScheduleStatus, ObjectiveFunction,
    ScheduleConstraint, ConstraintType, ConstraintPriority,
    WorkOrderSchedule, ScheduledOperation, ResourceInfo,
)

logger = logging.getLogger(__name__)


class SchedulingDomainService:
    def __init__(self) -> None:
        self._schedules: dict[str, ProductionSchedule] = {}

    def create_schedule(
        self,
        tenant_id: str,
        project_id: str,
        name: str,
        schedule_horizon_start: str = "",
        schedule_horizon_end: str = "",
        objective_function: ObjectiveFunction = ObjectiveFunction.MIN_MAKESPAN,
        created_by: str = "",
    ) -> ProductionSchedule:
        schedule = ProductionSchedule(
            tenant_id=tenant_id,
            project_id=project_id,
            name=name,
            schedule_horizon_start=schedule_horizon_start,
            schedule_horizon_end=schedule_horizon_end,
            objective_function=objective_function,
            created_by=created_by,
        )
        self._schedules[schedule.id] = schedule

        schedule.add_domain_event(DomainEvent(
            event_type="schedule.created",
            aggregate_id=schedule.id,
            payload={"schedule_id": schedule.id, "name": name},
        ))

        logger.info("Created production schedule %s", schedule.id)
        return schedule

    def add_work_order(
        self,
        schedule_id: str,
        work_order_id: str,
        work_order_code: str,
        priority: int = 0,
        due_date: str = "",
        operations: list[dict[str, Any]] | None = None,
    ) -> ProductionSchedule | None:
        schedule = self._schedules.get(schedule_id)
        if schedule is None:
            return None

        ops = []
        if operations:
            for op_data in operations:
                ops.append(ScheduledOperation(
                    work_order_id=work_order_id,
                    operation_name=op_data.get("operation_name", ""),
                    workstation=op_data.get("workstation", ""),
                    duration_hours=op_data.get("duration_hours", 1.0),
                    required_skills=op_data.get("required_skills", []),
                    required_materials=op_data.get("required_materials", []),
                    predecessor_ops=op_data.get("predecessor_ops", []),
                ))

        wo = WorkOrderSchedule(
            work_order_id=work_order_id,
            work_order_code=work_order_code,
            priority=priority,
            due_date=due_date,
            operations=ops,
        )
        schedule.work_orders.append(wo)
        return schedule

    def add_resource(
        self,
        schedule_id: str,
        resource_id: str,
        resource_name: str,
        resource_type: str = "workstation",
        capacity: int = 1,
        skills: list[str] | None = None,
        available_from: int = 0,
        available_to: int = 240,
    ) -> ProductionSchedule | None:
        schedule = self._schedules.get(schedule_id)
        if schedule is None:
            return None

        schedule.resources.append(ResourceInfo(
            resource_id=resource_id,
            resource_name=resource_name,
            resource_type=resource_type,
            capacity=capacity,
            skills=skills or [],
            available_from=available_from,
            available_to=available_to,
        ))
        return schedule

    def add_constraint(
        self,
        schedule_id: str,
        constraint_type: ConstraintType,
        constraint_expression: str,
        priority: ConstraintPriority = ConstraintPriority.HARD,
        description: str = "",
    ) -> ProductionSchedule | None:
        schedule = self._schedules.get(schedule_id)
        if schedule is None:
            return None

        schedule.constraints.append(ScheduleConstraint(
            constraint_type=constraint_type,
            constraint_expression=constraint_expression,
            priority=priority,
            description=description,
        ))
        return schedule

    def optimize_schedule(self, schedule_id: str) -> ProductionSchedule | None:
        schedule = self._schedules.get(schedule_id)
        if schedule is None:
            return None

        resource_timelines: dict[str, list[tuple[int, int]]] = {}
        for r in schedule.resources:
            resource_timelines[r.resource_id] = []

        current_time: dict[str, int] = {r.resource_id: r.available_from for r in schedule.resources}

        sorted_orders = sorted(schedule.work_orders, key=lambda wo: (-wo.priority, wo.due_date))

        gantt_data = []
        total_cost = 0.0

        for wo in sorted_orders:
            op_end_time = 0
            for op in wo.operations:
                ws = op.workstation
                if not ws and schedule.resources:
                    ws = schedule.resources[0].resource_id

                earliest = max(current_time.get(ws, 0), op_end_time)

                if op.predecessor_ops:
                    for pred_id in op.predecessor_ops:
                        for prev_gantt in gantt_data:
                            if prev_gantt.get("operation_name") == pred_id:
                                earliest = max(earliest, prev_gantt.get("end_time", 0))

                start = earliest
                end = start + int(op.duration_hours)

                op.start_time = start
                op.end_time = end
                op_end_time = end

                current_time[ws] = end

                resource_timelines.setdefault(ws, []).append((start, end))

                gantt_data.append({
                    "work_order_id": wo.work_order_id,
                    "work_order_code": wo.work_order_code,
                    "operation_name": op.operation_name,
                    "workstation": ws,
                    "start_time": start,
                    "end_time": end,
                    "duration_hours": op.duration_hours,
                    "is_critical": False,
                })

                cost = op.duration_hours * 100
                total_cost += cost

        if gantt_data:
            schedule.makespan_hours = max(g["end_time"] for g in gantt_data)
        schedule.total_cost = round(total_cost, 2)

        critical_path_end = schedule.makespan_hours
        for g in gantt_data:
            if g["end_time"] == critical_path_end:
                g["is_critical"] = True

        for r in schedule.resources:
            busy_hours = 0
            for start, end in resource_timelines.get(r.resource_id, []):
                busy_hours += end - start
            total_hours = r.available_to - r.available_from
            schedule.resource_utilization[r.resource_id] = round(
                busy_hours / max(total_hours, 1) * 100, 1
            )

        schedule.gantt_data = gantt_data
        schedule.conflicts = self._detect_conflicts(schedule)

        schedule.status = ScheduleStatus.OPTIMIZED
        schedule.add_domain_event(DomainEvent(
            event_type="schedule.optimized",
            aggregate_id=schedule.id,
            payload={"makespan": schedule.makespan_hours, "conflicts": len(schedule.conflicts)},
        ))

        logger.info("Schedule %s optimized: makespan=%.1fh, conflicts=%d",
                     schedule_id, schedule.makespan_hours, len(schedule.conflicts))
        return schedule

    def detect_conflicts(self, schedule_id: str) -> list[dict[str, Any]]:
        schedule = self._schedules.get(schedule_id)
        if schedule is None:
            return []
        return self._detect_conflicts(schedule)

    def what_if_analysis(
        self,
        schedule_id: str,
        params: dict[str, Any],
    ) -> dict[str, Any] | None:
        schedule = self._schedules.get(schedule_id)
        if schedule is None:
            return None

        original_makespan = schedule.makespan_hours
        original_util = dict(schedule.resource_utilization)
        original_conflicts = len(schedule.conflicts)

        extra_orders = params.get("add_work_orders", [])
        resource_changes = params.get("resource_changes", [])

        simulated_orders = list(schedule.work_orders)
        for wo_data in extra_orders:
            simulated_orders.append(WorkOrderSchedule(
                work_order_id=wo_data.get("work_order_id", ""),
                work_order_code=wo_data.get("work_order_code", ""),
                priority=wo_data.get("priority", 0),
                due_date=wo_data.get("due_date", ""),
            ))

        simulated_resources = list(schedule.resources)
        for rc in resource_changes:
            for r in simulated_resources:
                if r.resource_id == rc.get("resource_id"):
                    if "capacity" in rc:
                        r.capacity = rc["capacity"]
                    if "available_to" in rc:
                        r.available_to = rc["available_to"]

        return {
            "original": {
                "makespan_hours": original_makespan,
                "resource_utilization": original_util,
                "conflicts": original_conflicts,
            },
            "simulated": {
                "work_order_count": len(simulated_orders),
                "resource_count": len(simulated_resources),
                "note": "Run optimize to get full simulated results",
            },
        }

    def export_gantt_data(self, schedule_id: str) -> list[dict[str, Any]] | None:
        schedule = self._schedules.get(schedule_id)
        if schedule is None:
            return None
        return schedule.gantt_data

    def get_schedule(self, schedule_id: str) -> ProductionSchedule | None:
        return self._schedules.get(schedule_id)

    def list_schedules(
        self,
        tenant_id: str | None = None,
        project_id: str | None = None,
    ) -> list[ProductionSchedule]:
        schedules = list(self._schedules.values())
        if tenant_id:
            schedules = [s for s in schedules if s.tenant_id == tenant_id]
        if project_id:
            schedules = [s for s in schedules if s.project_id == project_id]
        return schedules

    def _detect_conflicts(self, schedule: ProductionSchedule) -> list[dict[str, Any]]:
        conflicts = []

        resource_ops: dict[str, list[dict[str, Any]]] = {}
        for g in schedule.gantt_data:
            ws = g.get("workstation", "")
            resource_ops.setdefault(ws, []).append(g)

        for ws, ops in resource_ops.items():
            sorted_ops = sorted(ops, key=lambda x: x.get("start_time", 0))
            for i in range(len(sorted_ops)):
                for j in range(i + 1, len(sorted_ops)):
                    op_i = sorted_ops[i]
                    op_j = sorted_ops[j]
                    if op_i.get("end_time", 0) > op_j.get("start_time", 0):
                        conflicts.append({
                            "type": "resource_conflict",
                            "resource": ws,
                            "operation_a": op_i.get("operation_name", ""),
                            "operation_b": op_j.get("operation_name", ""),
                            "description": f"资源 {ws} 上 {op_i.get('operation_name')} 和 {op_j.get('operation_name')} 时间冲突",
                        })

        for wo in schedule.work_orders:
            if wo.due_date:
                last_op = wo.operations[-1] if wo.operations else None
                if last_op and last_op.end_time > 0:
                    due_hours = 240
                    try:
                        due_hours = int(wo.due_date.split("-")[-1]) if "-" in wo.due_date else 240
                    except (ValueError, IndexError):
                        pass
                    if last_op.end_time > due_hours:
                        conflicts.append({
                            "type": "due_date_conflict",
                            "work_order": wo.work_order_code,
                            "end_time": last_op.end_time,
                            "due_date_hours": due_hours,
                            "description": f"工单 {wo.work_order_code} 完工时间超出交期",
                        })

        return conflicts