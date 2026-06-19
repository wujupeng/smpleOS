from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Any


@dataclass
class KnowledgeNode:
    node_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    graph_id: str = ""
    node_type: str = ""
    name: str = ""
    properties: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    embedding: Optional[list[float]] = None
    confidence: float = 1.0
    source: str = "manual"
    source_ref: Optional[str] = None
    version: int = 1
    is_inferred: bool = False
    created_by: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def update_properties(self, new_props: dict) -> None:
        self.properties.update(new_props)
        self.version += 1
        self.updated_at = datetime.now(timezone.utc)

    def add_tag(self, tag: str) -> None:
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> None:
        if tag in self.tags:
            self.tags.remove(tag)

    def set_embedding(self, embedding: list[float]) -> None:
        self.embedding = embedding

    def is_stale(self, threshold_days: int = 90) -> bool:
        delta = datetime.now(timezone.utc) - self.updated_at
        return delta.days > threshold_days


@dataclass
class RequirementNode(KnowledgeNode):
    node_type: str = "requirement"
    spec_id: Optional[str] = None
    parameter_name: Optional[str] = None
    parameter_value: Optional[Any] = None
    unit: Optional[str] = None
    is_mandatory: bool = True


@dataclass
class DesignNode(KnowledgeNode):
    node_type: str = "design"
    model_id: Optional[str] = None
    model_type: Optional[str] = None
    design_parameters: dict = field(default_factory=dict)


@dataclass
class StructureNode(KnowledgeNode):
    node_type: str = "structure"
    structure_type: Optional[str] = None
    material_ref: Optional[str] = None
    dimensions: dict = field(default_factory=dict)


@dataclass
class MaterialNode(KnowledgeNode):
    node_type: str = "material"
    material_class: Optional[str] = None
    density: Optional[float] = None
    tensile_strength: Optional[float] = None
    certification_status: Optional[str] = None


@dataclass
class ManufacturingNode(KnowledgeNode):
    node_type: str = "manufacturing"
    process_type: Optional[str] = None
    capability: dict = field(default_factory=dict)
    tooling_ref: Optional[str] = None


@dataclass
class FlightNode(KnowledgeNode):
    node_type: str = "flight"
    aircraft_serial: Optional[str] = None
    flight_hours: Optional[float] = None
    last_flight_date: Optional[datetime] = None


@dataclass
class MaintenanceNode(KnowledgeNode):
    node_type: str = "maintenance"
    aircraft_serial: Optional[str] = None
    maintenance_type: Optional[str] = None
    next_due_date: Optional[datetime] = None