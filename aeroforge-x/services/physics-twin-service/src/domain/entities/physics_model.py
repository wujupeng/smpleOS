from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.domain.enums import FidelityLevel, HierarchyLevel, ModelStatus, PhysicsType, COMPATIBILITY_RULES, FIDELITY_COMPATIBILITY


class PhysicsModel(BaseModel):
    model_id: str = ""
    name: str
    type: PhysicsType
    hierarchy_level: HierarchyLevel
    fidelity_level: FidelityLevel
    aircraft_object_id: str
    parameter_mappings: list[dict[str, Any]] = Field(default_factory=list)
    geometry_ref: str = ""
    status: ModelStatus = ModelStatus.Draft
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def validate_compatibility(self) -> dict[str, Any]:
        errors = []
        allowed_hierarchies = COMPATIBILITY_RULES.get(self.type.value, [])
        if self.hierarchy_level.value not in allowed_hierarchies:
            errors.append(f"{self.type.value} models are not compatible with {self.hierarchy_level.value} hierarchy level")

        allowed_fidelities = FIDELITY_COMPATIBILITY.get(self.hierarchy_level.value, [])
        if self.fidelity_level.value not in allowed_fidelities:
            errors.append(f"{self.hierarchy_level.value} hierarchy is not compatible with {self.fidelity_level.value} fidelity level")

        return {"valid": len(errors) == 0, "errors": errors}

    def switch_fidelity(self, level: FidelityLevel) -> None:
        allowed_fidelities = FIDELITY_COMPATIBILITY.get(self.hierarchy_level.value, [])
        if level.value not in allowed_fidelities:
            raise ValueError(f"Cannot switch to {level.value} fidelity for {self.hierarchy_level.value} hierarchy")
        self.fidelity_level = level
        self.updated_at = datetime.utcnow()