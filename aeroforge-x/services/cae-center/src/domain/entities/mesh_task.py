from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from aeroforge_common.domain.base import AggregateRoot, DomainEvent


class MeshTaskStatus(str, Enum):
    QUEUED = "queued"
    MESHING = "meshing"
    COMPLETED = "completed"
    FAILED = "failed"


class MeshType(str, Enum):
    STRUCTURED = "structured"
    UNSTRUCTURED = "unstructured"


@dataclass
class MeshQualityMetrics:
    orthogonality_min: float = 0.0
    orthogonality_avg: float = 0.0
    skewness_max: float = 0.0
    skewness_avg: float = 0.0
    aspect_ratio_max: float = 0.0
    aspect_ratio_avg: float = 0.0


class MeshTask(AggregateRoot):
    def __init__(
        self,
        model_id: str,
        mesh_type: MeshType,
        target_element_size: float = 0.01,
        task_id: str | None = None,
    ) -> None:
        super().__init__(task_id)
        self.model_id: str = model_id
        self.mesh_type: MeshType = mesh_type
        self.target_element_size: float = target_element_size
        self.status: MeshTaskStatus = MeshTaskStatus.QUEUED
        self.element_count: int = 0
        self.node_count: int = 0
        self.mesh_quality: MeshQualityMetrics | None = None
        self.output_path: str = ""
        self.error_message: str | None = None
        self.created_at: datetime = datetime.now(timezone.utc)
        self.updated_at: datetime = datetime.now(timezone.utc)
        self.extra_params: dict[str, Any] = field(default_factory=dict)

    def start_meshing(self) -> None:
        if self.status != MeshTaskStatus.QUEUED:
            raise ValueError(f"Cannot start meshing from status {self.status}")
        self.status = MeshTaskStatus.MESHING
        self.updated_at = datetime.now(timezone.utc)

    def complete(
        self,
        element_count: int,
        node_count: int,
        output_path: str,
        quality: MeshQualityMetrics | None = None,
    ) -> None:
        if self.status != MeshTaskStatus.MESHING:
            raise ValueError(f"Cannot complete from status {self.status}")
        self.status = MeshTaskStatus.COMPLETED
        self.element_count = element_count
        self.node_count = node_count
        self.output_path = output_path
        self.mesh_quality = quality
        self.updated_at = datetime.now(timezone.utc)
        self.add_domain_event(DomainEvent(
            event_type="mesh.task.completed",
            aggregate_id=self.id,
            payload={"model_id": self.model_id, "element_count": element_count},
        ))

    def fail(self, error_message: str) -> None:
        self.status = MeshTaskStatus.FAILED
        self.error_message = error_message
        self.updated_at = datetime.now(timezone.utc)
        self.add_domain_event(DomainEvent(
            event_type="mesh.task.failed",
            aggregate_id=self.id,
            payload={"model_id": self.model_id, "error": error_message},
        ))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "model_id": self.model_id,
            "mesh_type": self.mesh_type.value,
            "target_element_size": self.target_element_size,
            "status": self.status.value,
            "element_count": self.element_count,
            "node_count": self.node_count,
            "output_path": self.output_path,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }