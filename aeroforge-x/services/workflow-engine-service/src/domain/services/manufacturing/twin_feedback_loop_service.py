"""AeroForge-X v5.0 TwinFeedbackLoopService

Implements Twin→Design feedback loop with 7-stage state machine:
TWIN_DATA_COLLECTION → ROOT_CAUSE_ANALYSIS → DESIGN_UPDATE →
CAE_RERUN → BOM_UPDATE → MES_UPDATE → TWIN_UPDATE

Supports pause/resume, interrupt handling, and full audit trail.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class FeedbackLoopStage(str, Enum):
    TWIN_DATA_COLLECTION = "TwinDataCollection"
    ROOT_CAUSE_ANALYSIS = "RootCauseAnalysis"
    DESIGN_UPDATE = "DesignUpdate"
    CAE_RERUN = "CAERerun"
    BOM_UPDATE = "BOMUpdate"
    MES_UPDATE = "MESUpdate"
    TWIN_UPDATE = "TwinUpdate"


class FeedbackLoopStatus(str, Enum):
    RUNNING = "Running"
    PAUSED = "Paused"
    COMPLETED = "Completed"
    FAILED = "Failed"


class TriggerType(str, Enum):
    TWIN_ANOMALY = "TwinAnomaly"
    FRACAS_ALERT = "FRACASAlert"
    DESIGN_FEEDBACK = "DesignFeedback"


_STAGE_TRANSITIONS: dict[FeedbackLoopStage, FeedbackLoopStage] = {
    FeedbackLoopStage.TWIN_DATA_COLLECTION: FeedbackLoopStage.ROOT_CAUSE_ANALYSIS,
    FeedbackLoopStage.ROOT_CAUSE_ANALYSIS: FeedbackLoopStage.DESIGN_UPDATE,
    FeedbackLoopStage.DESIGN_UPDATE: FeedbackLoopStage.CAE_RERUN,
    FeedbackLoopStage.CAE_RERUN: FeedbackLoopStage.BOM_UPDATE,
    FeedbackLoopStage.BOM_UPDATE: FeedbackLoopStage.MES_UPDATE,
    FeedbackLoopStage.MES_UPDATE: FeedbackLoopStage.TWIN_UPDATE,
}


@dataclass(frozen=True)
class FeedbackTrigger:
    trigger_type: TriggerType
    trigger_data: dict


@dataclass
class StageTransitionRecord:
    from_stage: FeedbackLoopStage
    to_stage: FeedbackLoopStage
    timestamp: str
    operator_id: str
    notes: str = ""


@dataclass
class FeedbackLoopInstance:
    instance_id: str
    trigger: FeedbackTrigger
    current_stage: FeedbackLoopStage
    stage_history: list[StageTransitionRecord]
    design_update: dict
    cae_rerun_result: dict
    bom_update_result: dict
    mes_update_result: dict
    status: FeedbackLoopStatus
    created_at: str = ""
    completed_at: str = ""
    audit_trail: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "instance_id": self.instance_id,
            "trigger_type": self.trigger.trigger_type.value,
            "trigger_data": self.trigger.trigger_data,
            "current_stage": self.current_stage.value,
            "status": self.status.value,
            "stage_history": [
                {
                    "from_stage": r.from_stage.value,
                    "to_stage": r.to_stage.value,
                    "timestamp": r.timestamp,
                    "operator_id": r.operator_id,
                }
                for r in self.stage_history
            ],
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


class TwinFeedbackLoopService:

    def __init__(self) -> None:
        self._instances: dict[str, FeedbackLoopInstance] = {}

    def initiate_feedback_loop(
        self,
        trigger_type: str,
        trigger_data: dict,
    ) -> FeedbackLoopInstance:
        instance_id = f"FBL-{uuid.uuid4().hex[:8].upper()}"

        trigger = FeedbackTrigger(
            trigger_type=TriggerType(trigger_type),
            trigger_data=trigger_data,
        )

        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        instance = FeedbackLoopInstance(
            instance_id=instance_id,
            trigger=trigger,
            current_stage=FeedbackLoopStage.TWIN_DATA_COLLECTION,
            stage_history=[],
            design_update={},
            cae_rerun_result={},
            bom_update_result={},
            mes_update_result={},
            status=FeedbackLoopStatus.RUNNING,
            created_at=now,
            audit_trail=[{
                "timestamp": now,
                "action": "loop_initiated",
                "trigger_type": trigger_type,
                "operator": "system",
            }],
        )

        self._instances[instance_id] = instance
        return instance

    def advance_loop_stage(
        self,
        instance_id: str,
        operator_id: str = "system",
        stage_result: dict | None = None,
    ) -> FeedbackLoopInstance:
        instance = self._instances.get(instance_id)
        if instance is None:
            raise ValueError(f"Instance {instance_id} not found")

        if instance.status != FeedbackLoopStatus.RUNNING:
            raise ValueError(f"Cannot advance: loop status is {instance.status.value}")

        current = instance.current_stage
        next_stage = _STAGE_TRANSITIONS.get(current)

        if next_stage is None:
            instance.status = FeedbackLoopStatus.COMPLETED
            instance.completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            instance.audit_trail.append({
                "timestamp": now,
                "action": "loop_completed",
                "operator": operator_id,
            })
            return instance

        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        if current == FeedbackLoopStage.ROOT_CAUSE_ANALYSIS:
            if stage_result:
                instance.design_update = stage_result.get("design_update", {})
        elif current == FeedbackLoopStage.DESIGN_UPDATE:
            pass
        elif current == FeedbackLoopStage.CAE_RERUN:
            if stage_result:
                instance.cae_rerun_result = stage_result
                if not stage_result.get("passed", True):
                    instance.status = FeedbackLoopStatus.PAUSED
                    instance.audit_trail.append({
                        "timestamp": now,
                        "action": "cae_rerun_failed",
                        "operator": operator_id,
                        "detail": "CAE rerun did not pass — loop paused",
                    })
                    return instance
        elif current == FeedbackLoopStage.BOM_UPDATE:
            if stage_result:
                instance.bom_update_result = stage_result
        elif current == FeedbackLoopStage.MES_UPDATE:
            if stage_result:
                instance.mes_update_result = stage_result

        transition = StageTransitionRecord(
            from_stage=current,
            to_stage=next_stage,
            timestamp=now,
            operator_id=operator_id,
        )
        instance.stage_history.append(transition)
        instance.current_stage = next_stage

        instance.audit_trail.append({
            "timestamp": now,
            "action": "stage_advanced",
            "from_stage": current.value,
            "to_stage": next_stage.value,
            "operator": operator_id,
        })

        return instance

    def pause_loop(
        self,
        instance_id: str,
        operator_id: str = "system",
        reason: str = "",
    ) -> FeedbackLoopInstance:
        instance = self._instances.get(instance_id)
        if instance is None:
            raise ValueError(f"Instance {instance_id} not found")

        if instance.status != FeedbackLoopStatus.RUNNING:
            raise ValueError(f"Cannot pause: loop status is {instance.status.value}")

        instance.status = FeedbackLoopStatus.PAUSED
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        instance.audit_trail.append({
            "timestamp": now,
            "action": "loop_paused",
            "operator": operator_id,
            "reason": reason,
            "current_stage": instance.current_stage.value,
        })

        return instance

    def resume_loop(
        self,
        instance_id: str,
        operator_id: str = "system",
    ) -> FeedbackLoopInstance:
        instance = self._instances.get(instance_id)
        if instance is None:
            raise ValueError(f"Instance {instance_id} not found")

        if instance.status != FeedbackLoopStatus.PAUSED:
            raise ValueError(f"Cannot resume: loop status is {instance.status.value}")

        instance.status = FeedbackLoopStatus.RUNNING
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        instance.audit_trail.append({
            "timestamp": now,
            "action": "loop_resumed",
            "operator": operator_id,
            "current_stage": instance.current_stage.value,
        })

        return instance

    def get_loop_status(self, instance_id: str) -> Optional[FeedbackLoopInstance]:
        return self._instances.get(instance_id)

    def get_audit_trail(self, instance_id: str) -> list[dict]:
        instance = self._instances.get(instance_id)
        if instance is None:
            return []
        return list(instance.audit_trail)