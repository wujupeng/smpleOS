from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone
from typing import Any

from aeroforge_common.domain.base import DomainEvent

from ..entities.adaptive_schedule import (
    AdaptationRecord,
    AdaptationStatus,
    AdaptationTrigger,
    AdaptationTriggerType,
    AdaptiveSchedule,
    PerformanceMetrics,
    ScheduleStatus,
)

logger = logging.getLogger(__name__)


class AdaptiveSchedulingService:
    def __init__(self) -> None:
        self._schedules: dict[str, AdaptiveSchedule] = {}

    def create_adaptive_schedule(
        self,
        tenant_id: str,
        project_id: str,
        name: str,
        base_schedule: dict[str, Any] | None = None,
    ) -> AdaptiveSchedule:
        schedule = AdaptiveSchedule(
            tenant_id=tenant_id,
            project_id=project_id,
            name=name,
            base_schedule=base_schedule or {"operations": []},
        )

        self._schedules[schedule.id] = schedule

        schedule.add_domain_event(DomainEvent(
            event_type="adaptive_schedule.created",
            aggregate_id=schedule.id,
            payload={"tenant_id": tenant_id, "project_id": project_id, "name": name},
        ))

        logger.info("Adaptive schedule created: id=%s name=%s", schedule.id, name)
        return schedule

    def get_schedule(self, schedule_id: str) -> AdaptiveSchedule | None:
        return self._schedules.get(schedule_id)

    def monitor_schedule_execution(
        self,
        schedule_id: str,
        actual_progress: dict[str, Any],
    ) -> dict[str, Any]:
        schedule = self._schedules.get(schedule_id)
        if schedule is None:
            return {"error": "Schedule not found"}

        planned = schedule.current_schedule.get("operations", [])
        deviations: list[dict[str, Any]] = []

        for op in planned:
            op_id = op.get("operation_id", "")
            actual = actual_progress.get(op_id, {})
            planned_end = op.get("planned_end", "")
            actual_end = actual.get("actual_end", "")
            status = actual.get("status", "pending")

            if status == "delayed" or (planned_end and actual_end and actual_end > planned_end):
                deviations.append({
                    "operation_id": op_id,
                    "deviation_type": "delay",
                    "planned_end": planned_end,
                    "actual_end": actual_end,
                    "delay_hours": actual.get("delay_hours", 0),
                })

        return {
            "schedule_id": schedule_id,
            "total_operations": len(planned),
            "deviations": deviations,
            "deviation_count": len(deviations),
            "on_track": len(deviations) == 0,
        }

    def detect_adaptation_trigger(
        self,
        schedule_id: str,
        event_type: str,
        event_data: dict[str, Any],
    ) -> AdaptationTrigger | None:
        schedule = self._schedules.get(schedule_id)
        if schedule is None:
            return None

        try:
            trigger_type = AdaptationTriggerType(event_type)
        except ValueError:
            logger.warning("Unknown trigger type: %s", event_type)
            return None

        affected = event_data.get("affected_operations", [])
        description = event_data.get("description", f"{trigger_type.value} detected")

        severity_map = {
            AdaptationTriggerType.STATION_FAILURE: "high",
            AdaptationTriggerType.QUALITY_ANOMALY: "high",
            AdaptationTriggerType.URGENT_INSERT: "high",
            AdaptationTriggerType.MATERIAL_DELAY: "medium",
            AdaptationTriggerType.PERSONNEL_ABSENCE: "medium",
            AdaptationTriggerType.STATION_RECOVERY: "low",
            AdaptationTriggerType.DEADLINE_CHANGE: "medium",
        }

        trigger = AdaptationTrigger(
            trigger_id=f"TRG-{secrets.token_hex(4)}",
            trigger_type=trigger_type,
            description=description,
            affected_operations=affected,
            severity=severity_map.get(trigger_type, "medium"),
        )

        schedule.add_trigger(trigger)

        logger.info(
            "Adaptation trigger detected: schedule=%s type=%s affected=%d",
            schedule_id, trigger_type.value, len(affected),
        )
        return trigger

    def adapt_schedule(
        self,
        schedule_id: str,
        trigger_id: str,
        constraints: dict[str, Any] | None = None,
    ) -> AdaptationRecord:
        schedule = self._schedules.get(schedule_id)
        if schedule is None:
            raise ValueError("Schedule not found")

        trigger = None
        for t in schedule.adaptation_triggers:
            if t.trigger_id == trigger_id:
                trigger = t
                break

        if trigger is None:
            raise ValueError(f"Trigger '{trigger_id}' not found")

        original = dict(schedule.current_schedule)
        adjusted = self._compute_adjusted_schedule(schedule, trigger, constraints or {})

        impact = self._assess_impact(original, adjusted, trigger)

        record = AdaptationRecord(
            record_id=f"ADP-{secrets.token_hex(4)}",
            trigger=trigger,
            original_schedule=original,
            adjusted_schedule=adjusted,
            impact_assessment=impact,
            cost_impact=impact.get("additional_cost", 0),
            delay_impact_hours=impact.get("delay_hours", 0),
        )

        schedule.add_adaptation(record)

        schedule.add_domain_event(DomainEvent(
            event_type="adaptive_schedule.adapted",
            aggregate_id=schedule.id,
            payload={
                "trigger_type": trigger.trigger_type.value,
                "impact": impact,
            },
        ))

        logger.info(
            "Schedule adapted: schedule=%s trigger=%s cost=%.1f delay=%.1fh",
            schedule_id, trigger.trigger_type.value, record.cost_impact, record.delay_impact_hours,
        )
        return record

    def evaluate_adaptation_impact(
        self,
        schedule_id: str,
        trigger_id: str,
        constraints: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        schedule = self._schedules.get(schedule_id)
        if schedule is None:
            return {"error": "Schedule not found"}

        trigger = None
        for t in schedule.adaptation_triggers:
            if t.trigger_id == trigger_id:
                trigger = t
                break

        if trigger is None:
            return {"error": "Trigger not found"}

        original = dict(schedule.current_schedule)
        adjusted = self._compute_adjusted_schedule(schedule, trigger, constraints or {})
        return self._assess_impact(original, adjusted, trigger)

    def learn_from_history(self, schedule_id: str) -> dict[str, Any]:
        schedule = self._schedules.get(schedule_id)
        if schedule is None:
            return {"error": "Schedule not found"}

        history = schedule.adaptation_history
        if not history:
            return {"schedule_id": schedule_id, "patterns": [], "recommendations": []}

        trigger_counts: dict[str, int] = {}
        total_cost = 0.0
        total_delay = 0.0

        for record in history:
            tt = record.trigger.trigger_type.value
            trigger_counts[tt] = trigger_counts.get(tt, 0) + 1
            total_cost += record.cost_impact
            total_delay += record.delay_impact_hours

        patterns = sorted(trigger_counts.items(), key=lambda x: x[1], reverse=True)

        recommendations = []
        for trigger_type, count in patterns:
            if count >= 3:
                recommendations.append(
                    f"Frequent {trigger_type} ({count} times): Consider adding buffer time or backup resources"
                )

        if total_delay > 24:
            recommendations.append(f"Total delay {total_delay:.0f}h: Review scheduling parameters and buffer allocation")

        return {
            "schedule_id": schedule_id,
            "total_adaptations": len(history),
            "patterns": [{"trigger_type": t, "count": c} for t, c in patterns],
            "total_cost_impact": round(total_cost, 2),
            "total_delay_hours": round(total_delay, 1),
            "recommendations": recommendations,
        }

    def get_adaptation_history(self, schedule_id: str) -> list[dict[str, Any]]:
        schedule = self._schedules.get(schedule_id)
        if schedule is None:
            return []
        return [r.to_dict() for r in schedule.adaptation_history]

    def _compute_adjusted_schedule(
        self,
        schedule: AdaptiveSchedule,
        trigger: AdaptationTrigger,
        constraints: dict[str, Any],
    ) -> dict[str, Any]:
        current = dict(schedule.current_schedule)
        operations = list(current.get("operations", []))

        if trigger.trigger_type == AdaptationTriggerType.STATION_FAILURE:
            station_id = trigger.description.split()[-1] if trigger.description else ""
            for op in operations:
                if op.get("station_id") == station_id and op.get("status") == "planned":
                    op["status"] = "postponed"
                    op["postponement_reason"] = "station_failure"

            available_stations = constraints.get("backup_stations", [])
            if available_stations:
                for op in operations:
                    if op.get("status") == "postponed":
                        op["station_id"] = available_stations[0]
                        op["status"] = "rescheduled"

        elif trigger.trigger_type == AdaptationTriggerType.URGENT_INSERT:
            urgent_op = constraints.get("urgent_operation", {})
            if urgent_op:
                priority_ops = [op for op in operations if op.get("priority", 5) <= 2]
                insert_pos = len(priority_ops)
                urgent_op["status"] = "urgent"
                operations.insert(insert_pos, urgent_op)

        elif trigger.trigger_type == AdaptationTriggerType.MATERIAL_DELAY:
            for op_id in trigger.affected_operations:
                for op in operations:
                    if op.get("operation_id") == op_id:
                        delay_h = constraints.get("delay_hours", 4)
                        op["status"] = "delayed"
                        op["delay_hours"] = delay_h

        elif trigger.trigger_type == AdaptationTriggerType.QUALITY_ANOMALY:
            for op_id in trigger.affected_operations:
                for op in operations:
                    if op.get("operation_id") == op_id:
                        op["status"] = "suspended"
                        op["suspension_reason"] = "quality_anomaly"

        current["operations"] = operations
        return current

    def _assess_impact(
        self,
        original: dict[str, Any],
        adjusted: dict[str, Any],
        trigger: AdaptationTrigger,
    ) -> dict[str, Any]:
        orig_ops = original.get("operations", [])
        adj_ops = adjusted.get("operations", [])

        postponed = sum(1 for op in adj_ops if op.get("status") in ("postponed", "delayed", "suspended"))
        total_ops = len(adj_ops)

        avg_delay = sum(op.get("delay_hours", 0) for op in adj_ops) / max(total_ops, 1)
        additional_cost = postponed * 500 + avg_delay * 100

        return {
            "trigger_type": trigger.trigger_type.value,
            "operations_affected": postponed,
            "total_operations": total_ops,
            "delay_hours": round(avg_delay, 1),
            "additional_cost": round(additional_cost, 2),
            "utilization_impact": round(-postponed / max(total_ops, 1) * 100, 1),
            "on_time_rate_impact": round(-postponed / max(total_ops, 1) * 100, 1),
        }