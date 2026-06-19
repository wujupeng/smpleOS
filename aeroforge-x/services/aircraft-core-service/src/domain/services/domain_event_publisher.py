from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any


from pydantic import BaseModel


class FieldChange(BaseModel):
    field_path: str
    old_value: Any
    new_value: Any
    unit: str = ""
    schema_type: str = ""


class PropagationHint(BaseModel):
    hint_key: str
    affected_chains: list[str] = []
    affected_schemas: list[str] = []


class DomainEvent(BaseModel):
    event_id: str = ""
    event_type: str
    aggregate_id: str
    schema_version: int = 1
    changed_fields: list[FieldChange] = []
    propagation_hints: list[PropagationHint] = []
    timestamp: str = ""
    source_service: str = "aircraft-core-service"
    correlation_id: str = ""


PROPAGATION_HINT_RULES: dict[str, list[PropagationHint]] = {
    "design.geometry.wingspan": [
        PropagationHint(hint_key="design.geometry.wingspan", affected_chains=["DesignToCAE"], affected_schemas=["AircraftGeometry"]),
    ],
    "design.geometry.chord_length": [
        PropagationHint(hint_key="design.geometry.chord_length", affected_chains=["DesignToCAE"], affected_schemas=["AircraftGeometry"]),
    ],
    "design.structure.material_id": [
        PropagationHint(hint_key="design.structure.material_id", affected_chains=["DesignToCAE", "EBOMToMBOM"], affected_schemas=["AircraftStructure"]),
    ],
    "design.structure.design_weight": [
        PropagationHint(hint_key="design.structure.design_weight", affected_chains=["EBOMToMBOM"], affected_schemas=["AircraftStructure"]),
    ],
    "manufacturing.ebom.generated": [
        PropagationHint(hint_key="manufacturing.ebom.generated", affected_chains=["EBOMToMBOM"], affected_schemas=[]),
    ],
    "twin.anomaly.detected": [
        PropagationHint(hint_key="twin.anomaly.detected", affected_chains=["TwinToFRACAS"], affected_schemas=["AircraftCertification"]),
    ],
}


class DomainEventPublisher:

    _event_cache: list[DomainEvent] = []

    @staticmethod
    def publish_object_change_event(
        aggregate_id: str,
        changed_fields: list[FieldChange],
        event_type: str = "aeroforge.aircraft.object.updated",
    ) -> DomainEvent:
        hints = DomainEventPublisher.build_propagation_hints(changed_fields)

        event = DomainEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            aggregate_id=aggregate_id,
            changed_fields=changed_fields,
            propagation_hints=hints,
            timestamp=datetime.utcnow().isoformat(),
            correlation_id=str(uuid.uuid4()),
        )

        DomainEventPublisher._event_cache.append(event)
        return event

    @staticmethod
    def build_propagation_hints(changed_fields: list[FieldChange]) -> list[PropagationHint]:
        hints = []
        for field in changed_fields:
            for pattern, rule_hints in PROPAGATION_HINT_RULES.items():
                parts = pattern.split(".")
                if field.schema_type.lower() in parts and field.field_path in parts:
                    hints.extend(rule_hints)
                elif field.field_path == parts[-1]:
                    hints.extend(rule_hints)
        return hints

    @staticmethod
    def get_cached_events() -> list[DomainEvent]:
        return list(DomainEventPublisher._event_cache)

    @staticmethod
    def clear_cache() -> None:
        DomainEventPublisher._event_cache.clear()