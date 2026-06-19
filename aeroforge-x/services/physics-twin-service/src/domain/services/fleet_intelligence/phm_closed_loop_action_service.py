"""AeroForge-X PHM Closed-Loop Action Service

Transforms PHM from Analytics → Intelligence by closing the loop:
    Fault Prediction → Maintenance Suggestion → Work Order Generation →
    Resource Scheduling → Execution Result → Model Correction

Per PM directive: "not just predict RUL, but form a closed action loop"
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ActionPriority(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class WorkOrderStatus(str, Enum):
    DRAFT = "Draft"
    APPROVED = "Approved"
    SCHEDULED = "Scheduled"
    IN_PROGRESS = "InProgress"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"


class SchedulingResult(str, Enum):
    SCHEDULED = "Scheduled"
    DEFERRED = "Deferred"
    ESCALATED = "Escalated"


class CorrectionOutcome(str, Enum):
    IMPROVED = "Improved"
    NO_CHANGE = "NoChange"
    DEGRADED = "Degraded"


@dataclass
class MaintenanceSuggestion:
    suggestion_id: str
    prediction_id: str
    component_id: str
    suggested_action: str
    priority: ActionPriority
    rul_hours_remaining: float
    confidence: float
    rationale: str
    estimated_duration_hours: float = 0.0
    required_parts: list[str] = field(default_factory=list)
    required_skills: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "suggestion_id": self.suggestion_id,
            "prediction_id": self.prediction_id,
            "component_id": self.component_id,
            "suggested_action": self.suggested_action,
            "priority": self.priority.value,
            "rul_hours_remaining": self.rul_hours_remaining,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "estimated_duration_hours": self.estimated_duration_hours,
            "required_parts": self.required_parts,
            "required_skills": self.required_skills,
        }


@dataclass
class MaintenanceWorkOrder:
    order_id: str
    suggestion_id: str
    component_id: str
    action_description: str
    priority: ActionPriority
    status: WorkOrderStatus = WorkOrderStatus.DRAFT
    assigned_technician: str = ""
    scheduled_start: Optional[str] = None
    scheduled_end: Optional[str] = None
    actual_start: Optional[str] = None
    actual_end: Optional[str] = None
    parts_used: list[str] = field(default_factory=list)
    findings: str = ""

    def to_dict(self) -> dict:
        return {
            "order_id": self.order_id,
            "suggestion_id": self.suggestion_id,
            "component_id": self.component_id,
            "action_description": self.action_description,
            "priority": self.priority.value,
            "status": self.status.value,
            "assigned_technician": self.assigned_technician,
            "scheduled_start": self.scheduled_start,
            "scheduled_end": self.scheduled_end,
            "actual_start": self.actual_start,
            "actual_end": self.actual_end,
            "parts_used": self.parts_used,
            "findings": self.findings,
        }


@dataclass
class ResourceSchedule:
    schedule_id: str
    order_id: str
    bay_id: str
    technician_id: str
    scheduled_start: str
    scheduled_end: str
    result: SchedulingResult = SchedulingResult.SCHEDULED
    conflict_reason: str = ""

    def to_dict(self) -> dict:
        return {
            "schedule_id": self.schedule_id,
            "order_id": self.order_id,
            "bay_id": self.bay_id,
            "technician_id": self.technician_id,
            "scheduled_start": self.scheduled_start,
            "scheduled_end": self.scheduled_end,
            "result": self.result.value,
            "conflict_reason": self.conflict_reason,
        }


@dataclass
class ExecutionResult:
    execution_id: str
    order_id: str
    component_id: str
    action_taken: str
    parts_replaced: list[str] = field(default_factory=list)
    measurements: dict = field(default_factory=dict)
    technician_notes: str = ""
    completed_at: str = ""

    def to_dict(self) -> dict:
        return {
            "execution_id": self.execution_id,
            "order_id": self.order_id,
            "component_id": self.component_id,
            "action_taken": self.action_taken,
            "parts_replaced": self.parts_replaced,
            "measurements": self.measurements,
            "technician_notes": self.technician_notes,
            "completed_at": self.completed_at,
        }


@dataclass
class ModelCorrection:
    correction_id: str
    prediction_id: str
    execution_id: str
    predicted_rul: float
    actual_rul: float
    prediction_error: float
    correction_outcome: CorrectionOutcome
    model_adjustments: dict = field(default_factory=dict)
    corrected_at: str = ""

    def to_dict(self) -> dict:
        return {
            "correction_id": self.correction_id,
            "prediction_id": self.prediction_id,
            "execution_id": self.execution_id,
            "predicted_rul": self.predicted_rul,
            "actual_rul": self.actual_rul,
            "prediction_error": self.prediction_error,
            "correction_outcome": self.correction_outcome.value,
            "model_adjustments": self.model_adjustments,
            "corrected_at": self.corrected_at,
        }


class PHMClosedLoopActionService:

    def __init__(self, repo=None) -> None:
        self._repo = repo
        self._suggestions: dict[str, MaintenanceSuggestion] = {}
        self._work_orders: dict[str, MaintenanceWorkOrder] = {}
        self._schedules: dict[str, ResourceSchedule] = {}
        self._executions: dict[str, ExecutionResult] = {}
        self._corrections: dict[str, ModelCorrection] = {}
        self._technician_bays: dict[str, list[str]] = {}
        self._bay_availability: dict[str, bool] = {}

    def generateMaintenanceSuggestion(
        self,
        prediction_id: str,
        component_id: str,
        rul_hours: float,
        confidence: float,
    ) -> MaintenanceSuggestion:
        if rul_hours < 100:
            priority = ActionPriority.CRITICAL
        elif rul_hours < 500:
            priority = ActionPriority.HIGH
        elif rul_hours < 1000:
            priority = ActionPriority.MEDIUM
        else:
            priority = ActionPriority.LOW

        if rul_hours < 500:
            action = f"Schedule immediate inspection and preventive replacement for {component_id}"
        else:
            action = f"Monitor {component_id} and plan maintenance within {rul_hours * 0.8:.0f} flight hours"

        suggestion = MaintenanceSuggestion(
            suggestion_id=f"SUG-{uuid.uuid4().hex[:8]}",
            prediction_id=prediction_id,
            component_id=component_id,
            suggested_action=action,
            priority=priority,
            rul_hours_remaining=rul_hours,
            confidence=confidence,
            rationale=f"RUL={rul_hours:.0f}h, confidence={confidence:.2f}",
            estimated_duration_hours=8.0 if priority in (ActionPriority.CRITICAL, ActionPriority.HIGH) else 4.0,
        )
        self._suggestions[suggestion.suggestion_id] = suggestion
        return suggestion

    def generateWorkOrder(self, suggestion_id: str) -> MaintenanceWorkOrder:
        if suggestion_id not in self._suggestions:
            raise ValueError(f"Suggestion not found: {suggestion_id}")

        suggestion = self._suggestions[suggestion_id]
        order = MaintenanceWorkOrder(
            order_id=f"WO-{uuid.uuid4().hex[:8]}",
            suggestion_id=suggestion_id,
            component_id=suggestion.component_id,
            action_description=suggestion.suggested_action,
            priority=suggestion.priority,
        )
        self._work_orders[order.order_id] = order
        return order

    def scheduleResources(
        self,
        order_id: str,
        bay_id: str,
        technician_id: str,
        start: str,
        end: str,
    ) -> ResourceSchedule:
        if order_id not in self._work_orders:
            raise ValueError(f"Work order not found: {order_id}")

        conflict = not self._bay_availability.get(bay_id, True)
        schedule = ResourceSchedule(
            schedule_id=f"SCH-{uuid.uuid4().hex[:8]}",
            order_id=order_id,
            bay_id=bay_id,
            technician_id=technician_id,
            scheduled_start=start,
            scheduled_end=end,
            result=SchedulingResult.DEFERRED if conflict else SchedulingResult.SCHEDULED,
            conflict_reason="Bay already occupied" if conflict else "",
        )
        self._schedules[schedule.schedule_id] = schedule
        if not conflict:
            self._bay_availability[bay_id] = False
            self._work_orders[order_id].status = WorkOrderStatus.SCHEDULED
            self._work_orders[order_id].scheduled_start = start
            self._work_orders[order_id].scheduled_end = end
            self._work_orders[order_id].assigned_technician = technician_id

        return schedule

    def recordExecution(
        self,
        order_id: str,
        action_taken: str,
        parts_replaced: list[str] = None,
        measurements: dict = None,
        notes: str = "",
    ) -> ExecutionResult:
        if order_id not in self._work_orders:
            raise ValueError(f"Work order not found: {order_id}")

        execution = ExecutionResult(
            execution_id=f"EXE-{uuid.uuid4().hex[:8]}",
            order_id=order_id,
            component_id=self._work_orders[order_id].component_id,
            action_taken=action_taken,
            parts_replaced=parts_replaced or [],
            measurements=measurements or {},
            technician_notes=notes,
        )
        self._executions[execution.execution_id] = execution
        self._work_orders[order_id].status = WorkOrderStatus.COMPLETED

        bay_id = None
        for sch in self._schedules.values():
            if sch.order_id == order_id:
                bay_id = sch.bay_id
                break
        if bay_id:
            self._bay_availability[bay_id] = True

        return execution

    def correctModel(
        self,
        prediction_id: str,
        execution_id: str,
        predicted_rul: float,
        actual_rul: float,
    ) -> ModelCorrection:
        error = abs(predicted_rul - actual_rul)
        if error < predicted_rul * 0.1:
            outcome = CorrectionOutcome.IMPROVED
        elif error < predicted_rul * 0.3:
            outcome = CorrectionOutcome.NO_CHANGE
        else:
            outcome = CorrectionOutcome.DEGRADED

        adjustments = {}
        if outcome == CorrectionOutcome.DEGRADED:
            adjustments = {"learning_rate_factor": 0.5, "retrain_flag": True}
        elif outcome == CorrectionOutcome.NO_CHANGE:
            adjustments = {"calibration_offset": error * 0.1}

        correction = ModelCorrection(
            correction_id=f"COR-{uuid.uuid4().hex[:8]}",
            prediction_id=prediction_id,
            execution_id=execution_id,
            predicted_rul=predicted_rul,
            actual_rul=actual_rul,
            prediction_error=error,
            correction_outcome=outcome,
            model_adjustments=adjustments,
        )
        self._corrections[correction.correction_id] = correction
        return correction

    def getClosedLoopStatus(self, prediction_id: str) -> dict:
        suggestion = None
        for s in self._suggestions.values():
            if s.prediction_id == prediction_id:
                suggestion = s
                break
        if suggestion is None:
            return {"prediction_id": prediction_id, "loop_status": "NoAction"}

        order = None
        for wo in self._work_orders.values():
            if wo.suggestion_id == suggestion.suggestion_id:
                order = wo
                break

        execution = None
        if order:
            for ex in self._executions.values():
                if ex.order_id == order.order_id:
                    execution = ex
                    break

        correction = None
        for c in self._corrections.values():
            if c.prediction_id == prediction_id:
                correction = c
                break

        stages = {
            "prediction": True,
            "suggestion": suggestion is not None,
            "work_order": order is not None,
            "scheduled": order is not None and order.status in (WorkOrderStatus.SCHEDULED, WorkOrderStatus.IN_PROGRESS, WorkOrderStatus.COMPLETED),
            "executed": execution is not None,
            "model_corrected": correction is not None,
        }

        completed = sum(1 for v in stages.values() if v)
        return {
            "prediction_id": prediction_id,
            "loop_status": "Closed" if correction is not None else "Open",
            "completion_percentage": round(completed / len(stages) * 100, 1),
            "stages": stages,
        }