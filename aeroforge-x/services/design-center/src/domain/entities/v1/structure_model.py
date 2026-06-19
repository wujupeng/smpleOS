from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class StructureComponentType(str, Enum):
    SPAR = "spar"
    RIB = "rib"
    FRAME = "frame"
    SKIN_PANEL = "skin_panel"
    STRINGER = "stringer"
    BULKHEAD = "bulkhead"
    FITTING = "fitting"


class StructureStatus(str, Enum):
    DRAFT = "draft"
    GENERATED = "generated"
    VALIDATED = "validated"
    APPROVED = "approved"
    RELEASED = "released"


@dataclass
class StructureModel:
    structure_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    airframe_ref: str | None = None
    component_type: StructureComponentType = StructureComponentType.SPAR
    material: str | None = None
    geometry: dict[str, Any] = field(default_factory=dict)
    load_cases: list[dict[str, Any]] = field(default_factory=list)
    fasteners: list[dict[str, Any]] = field(default_factory=list)
    status: StructureStatus = StructureStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def mark_generated(self) -> None:
        self.status = StructureStatus.GENERATED
        self.updated_at = datetime.utcnow()

    def add_load_case(self, load_case: dict[str, Any]) -> None:
        self.load_cases.append(load_case)
        self.updated_at = datetime.utcnow()

    def check_interference(self, other: "StructureModel") -> list[str]:
        issues = []
        self_bbox = self.geometry.get("bounding_box", {})
        other_bbox = other.geometry.get("bounding_box", {})
        if self_bbox and other_bbox:
            if (self_bbox.get("min_x", 0) < other_bbox.get("max_x", 0) and
                self_bbox.get("max_x", 0) > other_bbox.get("min_x", 0) and
                self_bbox.get("min_y", 0) < other_bbox.get("max_y", 0) and
                self_bbox.get("max_y", 0) > other_bbox.get("min_y", 0) and
                self_bbox.get("min_z", 0) < other_bbox.get("max_z", 0) and
                self_bbox.get("max_z", 0) > other_bbox.get("min_z", 0)):
                issues.append(f"Interference between {self.component_type.value} and {other.component_type.value}")
        return issues