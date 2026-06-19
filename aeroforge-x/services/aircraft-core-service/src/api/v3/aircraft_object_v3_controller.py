from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.services.schema_migration_service import SchemaMigrationService
from src.domain.services.domain_event_publisher import DomainEventPublisher, FieldChange

router = APIRouter(prefix="/api/v3/aircraft-core/objects", tags=["Aircraft Object v3"])


@router.post("")
async def create_object_v3(body: dict[str, Any]):
    schema_data = body.get("schema_data", {})
    schema_type = body.get("schema_type")

    migration_result = SchemaMigrationService.migrate_dict_to_schema(schema_data, schema_type)
    if migration_result.get("status") == "unclassified":
        raise HTTPException(status_code=400, detail="Could not classify schema data")

    return {"status": "created", "schema_type": migration_result.get("schema_type"), "data": migration_result.get("data")}


@router.put("/{object_id}")
async def update_object_v3(object_id: str, body: dict[str, Any]):
    changed_fields_data = body.get("changed_fields", [])
    changed_fields = [
        FieldChange(
            field_path=f.get("field_path", ""),
            old_value=f.get("old_value"),
            new_value=f.get("new_value"),
            unit=f.get("unit", ""),
            schema_type=f.get("schema_type", ""),
        )
        for f in changed_fields_data
    ]

    event = DomainEventPublisher.publish_object_change_event(
        aggregate_id=object_id,
        changed_fields=changed_fields,
        event_type=body.get("event_type", "aeroforge.aircraft.object.updated"),
    )

    return {"object_id": object_id, "event_id": event.event_id, "propagation_hints": [h.model_dump() for h in event.propagation_hints]}


@router.post("/migrate-v2")
async def migrate_v2_objects(body: dict[str, Any]):
    objects = body.get("objects", [])
    target_schema_type = body.get("target_schema_type")
    return SchemaMigrationService.batch_migrate(objects, target_schema_type)