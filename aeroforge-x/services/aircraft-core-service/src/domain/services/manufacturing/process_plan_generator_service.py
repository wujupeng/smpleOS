"""AeroForge-X v5.0 ProcessPlanGeneratorService

Auto-generates process plans from MBOM with constraint validation
and delivery time optimization.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class OperationType(str, Enum):
    MACHINING = "Machining"
    ASSEMBLY = "Assembly"
    INSPECTION = "Inspection"
    HEAT_TREATMENT = "HeatTreatment"


class PlanStatus(str, Enum):
    DRAFT = "Draft"
    VALIDATED = "Validated"
    OPTIMIZED = "Optimized"
    RELEASED = "Released"


@dataclass
class ManufacturingOperation:
    operation_id: str
    operation_type: OperationType
    sequence_number: int
    part_number: str
    description: str
    estimated_time_hours: float
    resource_assignments: dict = field(default_factory=dict)
    predecessor_ids: list[str] = field(default_factory=list)
    quality_gates: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "operation_id": self.operation_id,
            "operation_type": self.operation_type.value,
            "sequence_number": self.sequence_number,
            "part_number": self.part_number,
            "description": self.description,
            "estimated_time_hours": self.estimated_time_hours,
            "resource_assignments": self.resource_assignments,
            "predecessor_ids": self.predecessor_ids,
            "quality_gates": self.quality_gates,
        }


@dataclass
class ProcessPlan:
    plan_id: str
    mbom_id: str
    version: int
    operations: list[ManufacturingOperation]
    total_lead_time_hours: float
    resource_requirements: dict
    status: PlanStatus = PlanStatus.DRAFT

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "mbom_id": self.mbom_id,
            "version": self.version,
            "operations": [op.to_dict() for op in self.operations],
            "total_lead_time_hours": self.total_lead_time_hours,
            "resource_requirements": self.resource_requirements,
            "status": self.status.value,
        }


@dataclass
class ValidationResult:
    is_valid: bool
    violations: list[dict]
    warnings: list[dict]


class ProcessPlanGeneratorService:

    def __init__(self) -> None:
        self._plans: dict[str, ProcessPlan] = {}

    def generate_process_plan(
        self,
        mbom_id: str,
        bom_nodes: list[dict] | None = None,
    ) -> ProcessPlan:
        plan_id = f"PP-{uuid.uuid4().hex[:8].upper()}"
        operations: list[ManufacturingOperation] = []
        seq = 0
        prev_id: str | None = None

        if bom_nodes:
            for node_data in bom_nodes:
                part_number = node_data.get("part_number", "")
                make_or_buy = node_data.get("make_or_buy", "Make")

                if make_or_buy == "Buy":
                    seq += 1
                    op = ManufacturingOperation(
                        operation_id=f"OP-{plan_id}-{seq:03d}",
                        operation_type=OperationType.INSPECTION,
                        sequence_number=seq,
                        part_number=part_number,
                        description=f"Incoming inspection for {part_number}",
                        estimated_time_hours=2.0,
                        quality_gates=["IQI-001"],
                    )
                    if prev_id:
                        op.predecessor_ids.append(prev_id)
                    operations.append(op)
                    prev_id = op.operation_id
                else:
                    seq += 1
                    mach_op = ManufacturingOperation(
                        operation_id=f"OP-{plan_id}-{seq:03d}",
                        operation_type=OperationType.MACHINING,
                        sequence_number=seq,
                        part_number=part_number,
                        description=f"Machine {part_number}",
                        estimated_time_hours=8.0,
                        resource_assignments={"machine": "CNC-5AX", "operator": "Level-3"},
                    )
                    if prev_id:
                        mach_op.predecessor_ids.append(prev_id)
                    operations.append(mach_op)
                    prev_id = mach_op.operation_id

                    seq += 1
                    insp_op = ManufacturingOperation(
                        operation_id=f"OP-{plan_id}-{seq:03d}",
                        operation_type=OperationType.INSPECTION,
                        sequence_number=seq,
                        part_number=part_number,
                        description=f"In-process inspection for {part_number}",
                        estimated_time_hours=1.0,
                        predecessor_ids=[mach_op.operation_id],
                        quality_gates=["FPI-001"],
                    )
                    operations.append(insp_op)
                    prev_id = insp_op.operation_id

        if bom_nodes and len(bom_nodes) > 1:
            seq += 1
            asm_op = ManufacturingOperation(
                operation_id=f"OP-{plan_id}-{seq:03d}",
                operation_type=OperationType.ASSEMBLY,
                sequence_number=seq,
                part_number="ASSY-001",
                description="Final assembly",
                estimated_time_hours=16.0,
                resource_assignments={"workstation": "ASM-01", "technicians": 3},
                predecessor_ids=[op.operation_id for op in operations if not op.predecessor_ids or op == operations[-1]],
            )
            operations.append(asm_op)

        total_lead_time = self._compute_lead_time(operations)

        resource_req: dict[str, int] = {}
        for op in operations:
            for resource in op.resource_assignments.values():
                if isinstance(resource, str):
                    resource_req[resource] = resource_req.get(resource, 0) + 1

        plan = ProcessPlan(
            plan_id=plan_id,
            mbom_id=mbom_id,
            version=1,
            operations=operations,
            total_lead_time_hours=total_lead_time,
            resource_requirements=resource_req,
        )
        self._plans[plan_id] = plan
        return plan

    def validate_process_plan(self, plan_id: str) -> ValidationResult:
        plan = self._plans.get(plan_id)
        if plan is None:
            return ValidationResult(
                is_valid=False,
                violations=[{"error": "Plan not found"}],
                warnings=[],
            )

        violations: list[dict] = []
        warnings: list[dict] = []

        op_ids = {op.operation_id for op in plan.operations}
        for op in plan.operations:
            for pred_id in op.predecessor_ids:
                if pred_id not in op_ids:
                    violations.append({
                        "type": "InvalidPredecessor",
                        "operation_id": op.operation_id,
                        "predecessor_id": pred_id,
                        "message": f"Predecessor {pred_id} not found in plan",
                    })

            if op.estimated_time_hours <= 0:
                violations.append({
                    "type": "InvalidTime",
                    "operation_id": op.operation_id,
                    "message": "Estimated time must be positive",
                })

        if not plan.operations:
            warnings.append({"type": "EmptyPlan", "message": "Plan has no operations"})

        plan.status = PlanStatus.VALIDATED if not violations else PlanStatus.DRAFT

        return ValidationResult(
            is_valid=len(violations) == 0,
            violations=violations,
            warnings=warnings,
        )

    def optimize_process_plan(self, plan_id: str) -> ProcessPlan:
        plan = self._plans.get(plan_id)
        if plan is None:
            raise ValueError(f"Plan {plan_id} not found")

        parallel_groups: dict[int, list[ManufacturingOperation]] = {}
        for op in plan.operations:
            level = len(op.predecessor_ids)
            parallel_groups.setdefault(level, []).append(op)

        optimized_ops: list[ManufacturingOperation] = []
        seq = 0
        for level in sorted(parallel_groups.keys()):
            for op in parallel_groups[level]:
                seq += 1
                op.sequence_number = seq
                optimized_ops.append(op)

        plan.operations = optimized_ops
        plan.total_lead_time_hours = self._compute_lead_time(optimized_ops)
        plan.status = PlanStatus.OPTIMIZED

        return plan

    def get_process_plan(self, plan_id: str) -> Optional[ProcessPlan]:
        return self._plans.get(plan_id)

    def _compute_lead_time(self, operations: list[ManufacturingOperation]) -> float:
        if not operations:
            return 0.0

        completion_times: dict[str, float] = {}
        max_time = 0.0

        for op in operations:
            pred_max = 0.0
            for pred_id in op.predecessor_ids:
                pred_max = max(pred_max, completion_times.get(pred_id, 0.0))

            completion = pred_max + op.estimated_time_hours
            completion_times[op.operation_id] = completion
            max_time = max(max_time, completion)

        return max_time