from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.schemas.enums import SchemaType
from src.domain.services.schema_registry_service import SchemaRegistryService
from src.domain.services.schema_migration_service import SchemaMigrationService

router = APIRouter(prefix="/api/v3/aircraft-core/schemas", tags=["Schema Registry v3"])


@router.post("")
async def register_schema(body: dict[str, Any]):
    result = SchemaRegistryService.register_schema(
        schema_name=body.get("schema_name", ""),
        schema_type=body.get("schema_type", ""),
        field_definitions=body.get("field_definitions", []),
    )
    return result


@router.get("")
async def list_schemas(schema_type: str | None = None):
    return SchemaRegistryService.list_schemas(schema_type)


@router.get("/{schema_id}")
async def get_schema(schema_id: str):
    result = SchemaRegistryService.get_schema(schema_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Schema not found")
    return result


@router.post("/{schema_id}/versions")
async def publish_schema_version(schema_id: str, body: dict[str, Any] | None = None):
    new_fields = body.get("field_definitions") if body else None
    result = SchemaRegistryService.publish_schema_version(schema_id, new_fields)
    if result is None:
        raise HTTPException(status_code=404, detail="Schema not found")
    if "error" in result:
        raise HTTPException(status_code=409, detail=result)
    return result


@router.post("/{schema_id}/versions/{version}/deprecate")
async def deprecate_schema_version(schema_id: str, version: int):
    result = SchemaRegistryService.deprecate_schema_version(schema_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Schema not found")
    return result


@router.post("/{schema_id}/migrate")
async def execute_schema_migration(schema_id: str, body: dict[str, Any]):
    objects = body.get("objects", [])
    return SchemaRegistryService.execute_migration(schema_id, objects)


@router.get("/{schema_id}/compatibility")
async def check_compatibility(schema_id: str, target_version: int | None = None):
    entry = SchemaRegistryService.get_schema(schema_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Schema not found")
    return SchemaRegistryService.validate_compatibility(entry["field_definitions"], entry["field_definitions"])


@router.post("/validate")
async def validate_schema_instance(body: dict[str, Any]):
    from src.domain.schemas.aircraft_geometry import AircraftGeometry
    from src.domain.schemas.aircraft_structure import AircraftStructure
    from src.domain.schemas.aircraft_propulsion import AircraftPropulsion
    from src.domain.schemas.aircraft_avionics import AircraftAvionics
    from src.domain.schemas.aircraft_flight_envelope import AircraftFlightEnvelope
    from src.domain.schemas.aircraft_certification import AircraftCertification

    schema_type = body.get("__schema_type__", "")
    data = {k: v for k, v in body.items() if not k.startswith("__")}

    schema_map = {
        "AircraftGeometry": AircraftGeometry,
        "AircraftStructure": AircraftStructure,
        "AircraftPropulsion": AircraftPropulsion,
        "AircraftAvionics": AircraftAvionics,
        "AircraftFlightEnvelope": AircraftFlightEnvelope,
        "AircraftCertification": AircraftCertification,
    }

    schema_cls = schema_map.get(schema_type)
    if schema_cls is None:
        raise HTTPException(status_code=400, detail=f"Unknown schema type: {schema_type}")

    try:
        instance = schema_cls(**data)
        return {"valid": True, "data": instance.to_dict()}
    except Exception as e:
        return {"valid": False, "errors": [str(e)]}


@router.post("/compute-derived")
async def compute_derived_params(body: dict[str, Any]):
    schema_type = body.get("__schema_type__", "")
    data = {k: v for k, v in body.items() if not k.startswith("__")}

    from src.domain.schemas.aircraft_geometry import AircraftGeometry
    if schema_type == "AircraftGeometry":
        try:
            instance = AircraftGeometry(**data)
            return {"aspect_ratio": instance.aspect_ratio}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    return {"derived": {}}