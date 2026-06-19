from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from aeroforge_common.domain.base import AggregateRoot


class PipelineStage(str, Enum):
    REQUIREMENTS_TO_DESIGN = "requirements_to_design"
    DESIGN_TO_ENGINEERING = "design_to_engineering"
    ENGINEERING_TO_CAE = "engineering_to_cae"
    DESIGN_TO_BOM = "design_to_bom"
    BOM_TO_MANUFACTURING = "bom_to_manufacturing"
    CERTIFICATION = "certification"
    FLIGHT_TEST = "flight_test"
    DELIVERY_PACKAGE = "delivery_package"


class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelineStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class StageOutput:
    stage: PipelineStage
    status: StageStatus = StageStatus.PENDING
    output_data: dict[str, Any] = field(default_factory=dict)
    started_at: str = ""
    completed_at: str = ""
    error_message: str = ""
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage.value,
            "status": self.status.value,
            "output_data": self.output_data,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error_message": self.error_message,
            "duration_seconds": round(self.duration_seconds, 1),
        }


class FullPipelineRun(AggregateRoot):
    def __init__(
        self,
        tenant_id: str,
        project_id: str,
        aircraft_spec: dict[str, Any] | None = None,
    ) -> None:
        super().__init__()
        self.tenant_id = tenant_id
        self.project_id = project_id
        self.aircraft_spec = aircraft_spec or {}
        self.stage_outputs: dict[PipelineStage, StageOutput] = {}
        self.status = PipelineStatus.PENDING
        self.current_stage: PipelineStage | None = None
        self.created_at = datetime.now(timezone.utc)
        self.completed_at: datetime | None = None

        for stage in PipelineStage:
            self.stage_outputs[stage] = StageOutput(stage=stage)

    def start_stage(self, stage: PipelineStage) -> None:
        self.current_stage = stage
        self.status = PipelineStatus.RUNNING
        output = self.stage_outputs[stage]
        output.status = StageStatus.RUNNING
        output.started_at = datetime.now(timezone.utc).isoformat()

    def complete_stage(
        self,
        stage: PipelineStage,
        output_data: dict[str, Any],
        duration: float = 0.0,
    ) -> None:
        output = self.stage_outputs[stage]
        output.status = StageStatus.COMPLETED
        output.output_data = output_data
        output.completed_at = datetime.now(timezone.utc).isoformat()
        output.duration_seconds = duration

    def fail_stage(self, stage: PipelineStage, error: str) -> None:
        output = self.stage_outputs[stage]
        output.status = StageStatus.FAILED
        output.error_message = error
        self.status = PipelineStatus.FAILED

    def skip_stage(self, stage: PipelineStage) -> None:
        self.stage_outputs[stage].status = StageStatus.SKIPPED

    def complete_pipeline(self) -> None:
        self.status = PipelineStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)

    def pause_pipeline(self) -> None:
        self.status = PipelineStatus.PAUSED

    def get_progress(self) -> dict[str, Any]:
        total = len(self.stage_outputs)
        completed = sum(1 for o in self.stage_outputs.values() if o.status == StageStatus.COMPLETED)
        skipped = sum(1 for o in self.stage_outputs.values() if o.status == StageStatus.SKIPPED)
        failed = sum(1 for o in self.stage_outputs.values() if o.status == StageStatus.FAILED)

        return {
            "pipeline_id": self.id,
            "status": self.status.value,
            "current_stage": self.current_stage.value if self.current_stage else None,
            "total_stages": total,
            "completed_stages": completed,
            "skipped_stages": skipped,
            "failed_stages": failed,
            "progress_pct": round((completed + skipped) / total * 100, 1),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "status": self.status.value,
            "current_stage": self.current_stage.value if self.current_stage else None,
            "progress": self.get_progress(),
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    def to_detail_dict(self) -> dict[str, Any]:
        base = self.to_dict()
        base.update({
            "aircraft_spec": self.aircraft_spec,
            "stages": {stage.value: output.to_dict() for stage, output in self.stage_outputs.items()},
        })
        return base