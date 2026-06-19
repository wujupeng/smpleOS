from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from aeroforge_common.domain.base import AggregateRoot, DomainEvent


class AerodynamicModel(str, Enum):
    STEADY = "steady"
    QUASI_STEADY = "quasi_steady"
    UNSTEADY = "unsteady"


class FlutterStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SpeedRange:
    min_speed_ms: float = 0.0
    max_speed_ms: float = 300.0
    speed_steps: int = 20

    def to_dict(self) -> dict[str, Any]:
        return {
            "min_speed_ms": self.min_speed_ms,
            "max_speed_ms": self.max_speed_ms,
            "speed_steps": self.speed_steps,
        }


@dataclass
class StructuralMode:
    mode_number: int
    natural_frequency_hz: float = 0.0
    damping_ratio: float = 0.0
    mode_shape: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode_number": self.mode_number,
            "natural_frequency_hz": self.natural_frequency_hz,
            "damping_ratio": self.damping_ratio,
            "mode_shape": self.mode_shape,
        }


@dataclass
class FlutterResultSummary:
    flutter_speed_ms: float = 0.0
    flutter_frequency_hz: float = 0.0
    flutter_margin: float = 0.0
    critical_mode: int = 1
    damping_trend: list[dict[str, float]] = field(default_factory=list)
    frequency_trend: list[dict[str, float]] = field(default_factory=list)
    divergence_speed_ms: float = 0.0
    meets_airworthiness: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "flutter_speed_ms": self.flutter_speed_ms,
            "flutter_frequency_hz": self.flutter_frequency_hz,
            "flutter_margin": self.flutter_margin,
            "critical_mode": self.critical_mode,
            "damping_trend": self.damping_trend,
            "frequency_trend": self.frequency_trend,
            "divergence_speed_ms": self.divergence_speed_ms,
            "meets_airworthiness": self.meets_airworthiness,
        }


class FlutterTask(AggregateRoot):
    def __init__(
        self,
        model_id: str,
        speed_range: SpeedRange | None = None,
        aerodynamic_model: AerodynamicModel = AerodynamicModel.QUASI_STEADY,
        mesh_task_id: str | None = None,
        task_id: str | None = None,
    ) -> None:
        super().__init__(task_id)
        self.model_id: str = model_id
        self.speed_range: SpeedRange = speed_range or SpeedRange()
        self.aerodynamic_model: AerodynamicModel = aerodynamic_model
        self.mesh_task_id: str | None = mesh_task_id
        self.structural_modes: list[StructuralMode] = []
        self.status: FlutterStatus = FlutterStatus.QUEUED
        self.result_summary: FlutterResultSummary | None = None
        self.error_message: str | None = None
        self.progress_percent: float = 0.0
        self.current_step: str = ""
        self.created_at: datetime = datetime.now(timezone.utc)
        self.updated_at: datetime = datetime.now(timezone.utc)
        self.completed_at: datetime | None = None

    def add_structural_mode(self, mode: StructuralMode) -> None:
        self.structural_modes.append(mode)

    def start_running(self) -> None:
        if self.status != FlutterStatus.QUEUED:
            raise ValueError(f"Cannot start from status {self.status}")
        self.status = FlutterStatus.RUNNING
        self.progress_percent = 10.0
        self.current_step = "extracting_modes"
        self.updated_at = datetime.now(timezone.utc)

    def complete(self, result: FlutterResultSummary) -> None:
        if self.status != FlutterStatus.RUNNING:
            raise ValueError(f"Cannot complete from status {self.status}")
        self.status = FlutterStatus.COMPLETED
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
                "task_type": "flutter",
                "model_id": self.model_id,
                "result_summary": result.to_dict(),
            },
        ))

    def fail(self, error_message: str) -> None:
        self.status = FlutterStatus.FAILED
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
            "speed_range": self.speed_range.to_dict(),
            "aerodynamic_model": self.aerodynamic_model.value,
            "mesh_task_id": self.mesh_task_id,
            "structural_modes": [m.to_dict() for m in self.structural_modes],
            "status": self.status.value,
            "result_summary": self.result_summary.to_dict() if self.result_summary else None,
            "error_message": self.error_message,
            "progress_percent": self.progress_percent,
            "current_step": self.current_step,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }