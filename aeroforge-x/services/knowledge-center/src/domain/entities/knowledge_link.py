from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Any


@dataclass
class KnowledgeLink:
    link_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    graph_id: str = ""
    source_node_id: str = ""
    target_node_id: str = ""
    link_type: str = ""
    weight: float = 1.0
    properties: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    bidirectional: bool = False
    is_inferred: bool = False
    version: int = 1
    created_by: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def update_weight(self, new_weight: float) -> None:
        if not 0 <= new_weight <= 1:
            raise ValueError("Weight must be between 0 and 1")
        self.weight = new_weight
        self.version += 1
        self.updated_at = datetime.now(timezone.utc)

    def update_confidence(self, new_confidence: float) -> None:
        if not 0 <= new_confidence <= 1:
            raise ValueError("Confidence must be between 0 and 1")
        self.confidence = new_confidence
        self.version += 1
        self.updated_at = datetime.now(timezone.utc)

    def update_properties(self, new_props: dict) -> None:
        self.properties.update(new_props)
        self.version += 1
        self.updated_at = datetime.now(timezone.utc)

    def involves_node(self, node_id: str) -> bool:
        return self.source_node_id == node_id or self.target_node_id == node_id

    def get_other_node(self, node_id: str) -> Optional[str]:
        if self.source_node_id == node_id:
            return self.target_node_id
        if self.target_node_id == node_id:
            return self.source_node_id
        return None