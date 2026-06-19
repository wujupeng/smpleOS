from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from src.domain.schemas.enums import SchemaStatus, SchemaType


SCHEMA_TYPE_CLASS_MAP: dict[str, str] = {
    SchemaType.AircraftGeometry: "AircraftGeometry",
    SchemaType.AircraftStructure: "AircraftStructure",
    SchemaType.AircraftPropulsion: "AircraftPropulsion",
    SchemaType.AircraftAvionics: "AircraftAvionics",
    SchemaType.AircraftFlightEnvelope: "AircraftFlightEnvelope",
    SchemaType.AircraftCertification: "AircraftCertification",
}


class SchemaRegistryService:

    _registry: dict[str, dict[str, Any]] = {}

    @classmethod
    def register_schema(cls, schema_name: str, schema_type: str, field_definitions: list[dict[str, Any]]) -> dict[str, Any]:
        schema_id = str(uuid.uuid4())
        entry = {
            "schema_id": schema_id,
            "schema_name": schema_name,
            "schema_type": schema_type,
            "version": 1,
            "status": SchemaStatus.Draft.value,
            "field_definitions": field_definitions,
            "compatible_with": [],
            "migration_path": {},
            "cross_schema_refs": [],
            "published_at": None,
            "created_at": datetime.utcnow().isoformat(),
        }
        cls._registry[schema_id] = entry
        return entry

    @classmethod
    def publish_schema_version(cls, schema_id: str, new_field_definitions: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
        entry = cls._registry.get(schema_id)
        if entry is None:
            return None

        old_version = entry["version"]
        new_version = old_version + 1

        compatibility = cls.validate_compatibility(
            entry["field_definitions"],
            new_field_definitions or entry["field_definitions"],
        )

        if not compatibility["compatible"]:
            return {"error": "Compatibility check failed", "issues": compatibility["issues"]}

        migration_path = cls.generate_migration_path(
            entry["field_definitions"],
            new_field_definitions or entry["field_definitions"],
        )

        entry["version"] = new_version
        entry["status"] = SchemaStatus.Published.value
        entry["compatible_with"] = entry.get("compatible_with", []) + [old_version]
        entry["migration_path"] = migration_path
        entry["field_definitions"] = new_field_definitions or entry["field_definitions"]
        entry["published_at"] = datetime.utcnow().isoformat()

        return entry

    @classmethod
    def deprecate_schema_version(cls, schema_id: str) -> dict[str, Any] | None:
        entry = cls._registry.get(schema_id)
        if entry is None:
            return None
        entry["status"] = SchemaStatus.Deprecated.value
        return entry

    @classmethod
    def validate_compatibility(cls, old_fields: list[dict], new_fields: list[dict]) -> dict[str, Any]:
        issues = []
        old_field_map = {f["field_name"]: f for f in old_fields}
        new_field_map = {f["field_name"]: f for f in new_fields}

        for name, old_def in old_field_map.items():
            if name not in new_field_map:
                issues.append(f"Field '{name}' removed without migration rule")
            elif old_def.get("data_type") != new_field_map[name].get("data_type"):
                issues.append(f"Field '{name}' type changed from {old_def.get('data_type')} to {new_field_map[name].get('data_type')}")

        for name, new_def in new_field_map.items():
            if name not in old_field_map:
                if new_def.get("is_required", False) and new_def.get("default_value") is None:
                    issues.append(f"New required field '{name}' added without default value")

        return {"compatible": len(issues) == 0, "issues": issues}

    @classmethod
    def generate_migration_path(cls, old_fields: list[dict], new_fields: list[dict]) -> dict[str, Any]:
        old_field_map = {f["field_name"]: f for f in old_fields}
        new_field_map = {f["field_name"]: f for f in new_fields}

        path = {"added": [], "removed": [], "modified": [], "unchanged": []}

        for name in new_field_map:
            if name not in old_field_map:
                path["added"].append({"field_name": name, "default_value": new_field_map[name].get("default_value")})
            elif old_field_map[name] != new_field_map[name]:
                path["modified"].append({"field_name": name, "old": old_field_map[name], "new": new_field_map[name]})
            else:
                path["unchanged"].append(name)

        for name in old_field_map:
            if name not in new_field_map:
                path["removed"].append({"field_name": name})

        return path

    @classmethod
    def execute_migration(cls, schema_id: str, objects: list[dict[str, Any]]) -> dict[str, Any]:
        entry = cls._registry.get(schema_id)
        if entry is None:
            return {"error": "Schema not found"}

        migration_path = entry.get("migration_path", {})
        migrated = []
        failed = []

        for obj in objects:
            try:
                result = dict(obj)
                for added_field in migration_path.get("added", []):
                    if added_field["field_name"] not in result:
                        result[added_field["field_name"]] = added_field.get("default_value")
                for removed_field in migration_path.get("removed", []):
                    result.pop(removed_field["field_name"], None)
                migrated.append(result)
            except Exception as e:
                failed.append({"object_id": obj.get("id", "unknown"), "error": str(e)})

        return {"migrated_count": len(migrated), "failed_count": len(failed), "failed_objects": failed}

    @classmethod
    def validate_cross_schema_ref(cls, ref_field: str, ref_schema_type: str) -> dict[str, Any]:
        valid_types = set(SCHEMA_TYPE_CLASS_MAP.values())
        if ref_schema_type not in valid_types:
            return {"valid": False, "error": f"Unknown schema type: {ref_schema_type}"}
        return {"valid": True}

    @classmethod
    def get_schema(cls, schema_id: str) -> dict[str, Any] | None:
        return cls._registry.get(schema_id)

    @classmethod
    def list_schemas(cls, schema_type: str | None = None) -> list[dict[str, Any]]:
        if schema_type:
            return [v for v in cls._registry.values() if v["schema_type"] == schema_type]
        return list(cls._registry.values())