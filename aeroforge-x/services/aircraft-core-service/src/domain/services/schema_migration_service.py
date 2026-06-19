from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from src.domain.schemas.enums import SchemaType


SCHEMA_TYPE_INFERENCE_RULES: list[dict[str, Any]] = [
    {"schema_type": SchemaType.AircraftGeometry, "key_patterns": ["wingspan", "chord_length", "sweep_angle", "wing_area", "taper_ratio"]},
    {"schema_type": SchemaType.AircraftStructure, "key_patterns": ["material_id", "material_density", "yield_strength", "design_weight", "skin_thickness"]},
    {"schema_type": SchemaType.AircraftPropulsion, "key_patterns": ["engine_type", "max_thrust", "sfc", "bypass_ratio", "battery_capacity"]},
    {"schema_type": SchemaType.AircraftAvionics, "key_patterns": ["control_law_type", "elevator_limit", "aileron_limit", "sas_pitch_gain"]},
    {"schema_type": SchemaType.AircraftFlightEnvelope, "key_patterns": ["V_s", "V_A", "V_C", "V_D", "h_max", "n_max"]},
    {"schema_type": SchemaType.AircraftCertification, "key_patterns": ["clause_number", "compliance_status", "compliance_method"]},
]

SCHEMA_CLASS_MAP: dict[str, str] = {
    SchemaType.AircraftGeometry: "AircraftGeometry",
    SchemaType.AircraftStructure: "AircraftStructure",
    SchemaType.AircraftPropulsion: "AircraftPropulsion",
    SchemaType.AircraftAvionics: "AircraftAvionics",
    SchemaType.AircraftFlightEnvelope: "AircraftFlightEnvelope",
    SchemaType.AircraftCertification: "AircraftCertification",
}


class SchemaMigrationService:

    @staticmethod
    def infer_schema_type(data: dict[str, Any]) -> str | None:
        keys = set(data.keys())
        best_match = None
        best_score = 0

        for rule in SCHEMA_TYPE_INFERENCE_RULES:
            score = len(keys & set(rule["key_patterns"]))
            if score > best_score:
                best_score = score
                best_match = rule["schema_type"]

        if best_match and best_score >= 2:
            return best_match.value
        return None

    @staticmethod
    def migrate_dict_to_schema(data: dict[str, Any], target_schema_type: str | None = None) -> dict[str, Any]:
        schema_type = target_schema_type or SchemaMigrationService.infer_schema_type(data)
        if schema_type is None:
            return {"status": "unclassified", "original_data": data, "error": "Could not infer schema type"}

        from src.domain.services.attribute_name_service import AttributeNameService
        resolved_data = {}
        for key, value in data.items():
            resolution = AttributeNameService.resolve_name(key)
            canonical = resolution["canonical_name"]
            resolved_data[canonical] = value

        result = {
            "__schema_type__": schema_type,
            "__schema_version__": 1,
            **resolved_data,
        }

        extra_fields = {k: v for k, v in data.items() if AttributeNameService.resolve_name(k).get("unknown", False)}
        if extra_fields:
            result["extra_fields"] = extra_fields

        return {"status": "migrated", "schema_type": schema_type, "data": result}

    @staticmethod
    def apply_alias_mapping(data: dict[str, Any]) -> dict[str, Any]:
        from src.domain.services.attribute_name_service import AttributeNameService
        result = {}
        for key, value in data.items():
            resolution = AttributeNameService.resolve_name(key)
            result[resolution["canonical_name"]] = value
        return result

    @staticmethod
    def populate_defaults(data: dict[str, Any], schema_type: str) -> dict[str, Any]:
        defaults_map: dict[str, dict[str, Any]] = {
            SchemaType.AircraftGeometry.value: {"dihedral_angle": 0.0, "incidence_angle": 0.0},
            SchemaType.AircraftStructure.value: {"manufacturing_weight": 0.0, "weight_margin": 0.0},
            SchemaType.AircraftFlightEnvelope.value: {"n_min": -1.0, "n_max": 3.5},
        }
        defaults = defaults_map.get(schema_type, {})
        for key, value in defaults.items():
            if key not in data:
                data[key] = value
        return data

    @staticmethod
    def extract_extra_fields(data: dict[str, Any], known_fields: set[str]) -> dict[str, Any]:
        return {k: v for k, v in data.items() if k not in known_fields and not k.startswith("__")}

    @staticmethod
    def validate_migration_result(result: dict[str, Any]) -> dict[str, Any]:
        if result.get("status") == "unclassified":
            return {"valid": False, "error": result.get("error", "Unknown schema type")}
        data = result.get("data", {})
        if "__schema_type__" not in data:
            return {"valid": False, "error": "Missing __schema_type__ marker"}
        return {"valid": True}

    @staticmethod
    def batch_migrate(objects: list[dict[str, Any]], target_schema_type: str | None = None) -> dict[str, Any]:
        migrated = []
        failed = []

        for obj in objects:
            try:
                result = SchemaMigrationService.migrate_dict_to_schema(obj, target_schema_type)
                validation = SchemaMigrationService.validate_migration_result(result)
                if validation["valid"]:
                    migrated.append(result)
                else:
                    failed.append({"object_id": obj.get("id", "unknown"), "error": validation.get("error")})
            except Exception as e:
                failed.append({"object_id": obj.get("id", "unknown"), "error": str(e)})

        return {"migrated_count": len(migrated), "failed_count": len(failed), "failed_objects": failed}