from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.domain.enums import (
    AircraftObjectId,
    LifecycleState,
    LinkType,
    ObjectType,
    OBJECT_TYPE_HIERARCHY,
    VALID_TRANSITIONS,
    TRANSITION_VALIDATION_RULES,
    BaselineType,
)
from src.domain.value_objects.aircraft_object_link import AircraftObjectLink
from src.domain.value_objects.aircraft_property import AircraftProperty


class AircraftObject(BaseModel):
    id: str = Field(default_factory=lambda: "")
    object_type: ObjectType
    name: str
    lifecycle_state: LifecycleState = LifecycleState.Concept
    design_data: dict[str, Any] = Field(default_factory=dict)
    manufacturing_data: dict[str, Any] = Field(default_factory=dict)
    operation_data: dict[str, Any] = Field(default_factory=dict)
    certification_data: dict[str, Any] = Field(default_factory=dict)
    optimistic_lock_version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    links: list[AircraftObjectLink] = Field(default_factory=list, exclude=True)
    properties: list[AircraftProperty] = Field(default_factory=list, exclude=True)

    def generate_id(self) -> str:
        type_prefix_map = {
            ObjectType.Aircraft: "AC",
            ObjectType.System: "SY",
            ObjectType.Subsystem: "SS",
            ObjectType.Component: "CP",
            ObjectType.Part: "PT",
        }
        prefix = type_prefix_map.get(self.object_type, "OB")
        serial = uuid.uuid4().hex[:8].upper()
        self.id = f"AOBJ-{prefix}-{serial}"
        return self.id

    def transition_to(self, target: LifecycleState, validation_data: dict[str, bool] | None = None) -> None:
        if target not in VALID_TRANSITIONS.get(self.lifecycle_state, []):
            raise ValueError(f"Invalid transition from {self.lifecycle_state.value} to {target.value}")

        rule_key = (self.lifecycle_state, target)
        required_checks = TRANSITION_VALIDATION_RULES.get(rule_key, [])

        if required_checks and validation_data:
            missing = [check for check in required_checks if not validation_data.get(check, False)]
            if missing:
                raise ValueError(f"Cannot transition to {target.value}: missing validations: {missing}")

        self.lifecycle_state = target
        self.updated_at = datetime.utcnow()

    def add_property(self, prop: AircraftProperty) -> None:
        existing = [p for p in self.properties if p.property_def_id == prop.property_def_id]
        if existing:
            self.properties.remove(existing[0])
        self.properties.append(prop)
        self.updated_at = datetime.utcnow()

    def add_link(self, link: AircraftObjectLink) -> None:
        if link.source_id != self.id and link.target_id != self.id:
            raise ValueError("Link must involve this object")
        self.links.append(link)
        self.updated_at = datetime.utcnow()

    def create_version(self, summary: str, author: str) -> dict[str, Any]:
        from src.domain.entities.aircraft_object_version import AircraftObjectVersion

        snapshot = self.model_dump(exclude={"links", "properties"})
        version_number = getattr(self, "_next_version_number", 1)

        version = AircraftObjectVersion(
            version_id=f"AVER-{self.id}-{version_number}",
            object_id=self.id,
            version_number=version_number,
            snapshot=snapshot,
            change_summary=summary,
            author=author,
            baseline_type=BaselineType.None_,
            is_frozen=False,
        )

        if not hasattr(self, "_next_version_number"):
            self._next_version_number = 2
        else:
            self._next_version_number += 1

        self.updated_at = datetime.utcnow()
        return version.model_dump()

    @staticmethod
    def validate_parent_child_type(parent_type: ObjectType, child_type: ObjectType) -> bool:
        allowed_children = OBJECT_TYPE_HIERARCHY.get(parent_type, [])
        return child_type in allowed_children