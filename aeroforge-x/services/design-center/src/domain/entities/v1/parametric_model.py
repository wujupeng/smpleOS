from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ModelType(str, Enum):
    AIRFRAME = "airframe"
    STRUCTURE = "structure"
    POWERTRAIN = "powertrain"
    WIRE_HARNESS = "wire_harness"
    FULL_ASSEMBLY = "full_assembly"


class ModelStatus(str, Enum):
    DRAFT = "draft"
    GENERATED = "generated"
    VALIDATED = "validated"
    APPROVED = "approved"
    RELEASED = "released"
    ARCHIVED = "archived"

    def can_transition_to(self, target: "ModelStatus") -> bool:
        transitions = {
            ModelStatus.DRAFT: {ModelStatus.GENERATED},
            ModelStatus.GENERATED: {ModelStatus.VALIDATED, ModelStatus.DRAFT},
            ModelStatus.VALIDATED: {ModelStatus.APPROVED, ModelStatus.GENERATED},
            ModelStatus.APPROVED: {ModelStatus.RELEASED},
            ModelStatus.RELEASED: {ModelStatus.ARCHIVED},
            ModelStatus.ARCHIVED: set(),
        }
        return target in transitions.get(self, set())


@dataclass
class ParametricModel:
    model_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    spec_ref: str | None = None
    model_name: str = ""
    model_type: ModelType = ModelType.FULL_ASSEMBLY
    parameters: dict[str, Any] = field(default_factory=dict)
    constraints: list[dict[str, Any]] = field(default_factory=list)
    version: int = 1
    status: ModelStatus = ModelStatus.DRAFT
    geometry_data: dict[str, Any] | None = None
    created_by: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    domain_events: list[dict[str, Any]] = field(default_factory=list)

    def update_parameters(self, updates: dict[str, Any]) -> None:
        if self.status == ModelStatus.RELEASED or self.status == ModelStatus.ARCHIVED:
            raise ValueError(f"Cannot update parameters of model in {self.status.value} status")
        self.parameters.update(updates)
        self.updated_at = datetime.utcnow()

    def set_geometry(self, geometry: dict[str, Any]) -> None:
        self.geometry_data = geometry
        self.updated_at = datetime.utcnow()

    def mark_generated(self) -> None:
        if not self.status.can_transition_to(ModelStatus.GENERATED):
            raise ValueError(f"Cannot transition from {self.status.value} to generated")
        self.status = ModelStatus.GENERATED
        self.updated_at = datetime.utcnow()
        self.domain_events.append({
            "event_type": "parametric_model.generated",
            "model_id": self.model_id,
            "model_type": self.model_type.value,
        })

    def mark_validated(self) -> None:
        if not self.status.can_transition_to(ModelStatus.VALIDATED):
            raise ValueError(f"Cannot transition from {self.status.value} to validated")
        self.status = ModelStatus.VALIDATED
        self.updated_at = datetime.utcnow()

    def mark_approved(self) -> None:
        if not self.status.can_transition_to(ModelStatus.APPROVED):
            raise ValueError(f"Cannot transition from {self.status.value} to approved")
        self.status = ModelStatus.APPROVED
        self.updated_at = datetime.utcnow()

    def mark_released(self) -> None:
        if not self.status.can_transition_to(ModelStatus.RELEASED):
            raise ValueError(f"Cannot transition from {self.status.value} to released")
        self.status = ModelStatus.RELEASED
        self.updated_at = datetime.utcnow()

    def clear_events(self) -> list[dict[str, Any]]:
        events = self.domain_events.copy()
        self.domain_events.clear()
        return events