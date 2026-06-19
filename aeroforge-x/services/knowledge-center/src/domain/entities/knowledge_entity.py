from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from aeroforge_common.domain.base import AggregateRoot


class EntityType(str, Enum):
    REGULATION = "Regulation"
    MATERIAL = "Material"
    PROCESS = "Process"
    COMPONENT = "Component"
    FAILURE_MODE = "FailureMode"
    DESIGN_RULE = "DesignRule"
    BEST_PRACTICE = "BestPractice"


@dataclass
class SourceReference:
    source_id: str
    source_type: str
    title: str
    url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type,
            "title": self.title,
            "url": self.url,
        }


@dataclass
class KnowledgeRelation:
    relation_id: str
    from_entity_id: str
    to_entity_id: str
    relation_type: str
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "relation_id": self.relation_id,
            "from_entity_id": self.from_entity_id,
            "to_entity_id": self.to_entity_id,
            "relation_type": self.relation_type,
            "properties": self.properties,
        }


class KnowledgeEntity(AggregateRoot):
    def __init__(
        self,
        tenant_id: str,
        entity_type: EntityType,
        name: str,
        description: str = "",
    ) -> None:
        super().__init__()
        self.tenant_id = tenant_id
        self.entity_type = entity_type
        self.name = name
        self.description = description
        self.attributes: dict[str, Any] = {}
        self.source_references: list[SourceReference] = []
        self.relations: list[KnowledgeRelation] = []
        self.confidence: float = 1.0
        self.version: int = 1
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def set_attributes(self, attrs: dict[str, Any]) -> None:
        self.attributes = attrs
        self.updated_at = datetime.now(timezone.utc)

    def add_source_reference(self, ref: SourceReference) -> None:
        self.source_references.append(ref)

    def add_relation(self, relation: KnowledgeRelation) -> None:
        self.relations.append(relation)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "entity_type": self.entity_type.value,
            "name": self.name,
            "description": self.description,
            "confidence": self.confidence,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def to_detail_dict(self) -> dict[str, Any]:
        base = self.to_dict()
        base.update({
            "attributes": self.attributes,
            "source_references": [r.to_dict() for r in self.source_references],
            "relations": [r.to_dict() for r in self.relations],
        })
        return base