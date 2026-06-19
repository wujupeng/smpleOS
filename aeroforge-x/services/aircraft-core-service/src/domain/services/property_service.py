from __future__ import annotations

import uuid
from typing import Any

from src.domain.entities.property_definition import PropertyDefinition
from src.domain.enums import DataType, PropertyType, SourceTag
from src.domain.value_objects.aircraft_property import AircraftProperty


UNIT_CONVERSIONS: dict[tuple[str, str], float] = {
    ("m", "mm"): 1000.0,
    ("mm", "m"): 0.001,
    ("m", "cm"): 100.0,
    ("cm", "m"): 0.01,
    ("kg", "g"): 1000.0,
    ("g", "kg"): 0.001,
    ("Pa", "MPa"): 1e-6,
    ("MPa", "Pa"): 1e6,
    ("N", "kN"): 0.001,
    ("kN", "N"): 1000.0,
}

UNIT_DIMENSIONS: dict[str, str] = {
    "m": "length", "mm": "length", "cm": "length",
    "kg": "mass", "g": "mass",
    "Pa": "pressure", "MPa": "pressure",
    "N": "force", "kN": "force",
    "s": "time",
    "K": "temperature", "C": "temperature",
}


class PropertyService:

    @staticmethod
    async def create_property_definition(
        name: str,
        property_type: PropertyType,
        data_type: DataType,
        unit: str,
        constraints: dict[str, Any] | None = None,
        applicable_object_types: list[str] | None = None,
        derivation_formula: str | None = None,
        pool=None,
    ) -> PropertyDefinition:
        prop_def = PropertyDefinition(
            id=str(uuid.uuid4()),
            name=name,
            property_type=property_type,
            data_type=data_type,
            unit=unit,
            constraints=constraints or {},
            applicable_object_types=applicable_object_types or [],
            derivation_formula=derivation_formula,
        )

        if pool:
            async with pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO aircraft_core.property_definitions (id, name, property_type, data_type, unit, constraints, applicable_object_types, derivation_formula) "
                    "VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
                    prop_def.id, name, property_type.value, data_type.value, unit,
                    constraints or {}, applicable_object_types or [], derivation_formula,
                )

        return prop_def

    @staticmethod
    async def get_property_definition(prop_def_id: str, pool) -> PropertyDefinition | None:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM aircraft_core.property_definitions WHERE id = $1", prop_def_id
            )
            if row is None:
                return None
            return PropertyDefinition(**dict(row))

    @staticmethod
    async def set_property_value(
        object_id: str,
        property_def_id: str,
        value: Any,
        source: SourceTag,
        source_detail: str = "",
        confidence: float = 1.0,
        version_id: str = "",
        pool=None,
    ) -> AircraftProperty:
        prop_def = await PropertyService.get_property_definition(property_def_id, pool)
        if prop_def and not prop_def.validate_value(value):
            raise ValueError(f"Value {value} does not satisfy constraints for property {prop_def.name}")

        prop = AircraftProperty(
            value_id=str(uuid.uuid4()),
            object_id=object_id,
            property_def_id=property_def_id,
            value=value,
            unit=prop_def.unit if prop_def else "",
            source=source,
            source_detail=source_detail,
            confidence=confidence,
            version_id=version_id,
        )

        if pool:
            async with pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO aircraft_core.aircraft_property_values (value_id, object_id, property_definition_id, value, source_tag, source_detail, confidence, version_id) "
                    "VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
                    prop.value_id, object_id, property_def_id, value,
                    source.value, source_detail, confidence, version_id,
                )

        return prop

    @staticmethod
    async def get_object_properties(
        object_id: str,
        property_type: PropertyType | None = None,
        pool=None,
    ) -> list[AircraftProperty]:
        async with pool.acquire() as conn:
            if property_type:
                rows = await conn.fetch(
                    "SELECT pv.*, pd.property_type FROM aircraft_core.aircraft_property_values pv "
                    "JOIN aircraft_core.property_definitions pd ON pv.property_definition_id = pd.id "
                    "WHERE pv.object_id = $1 AND pd.property_type = $2",
                    object_id, property_type.value,
                )
            else:
                rows = await conn.fetch(
                    "SELECT * FROM aircraft_core.aircraft_property_values WHERE object_id = $1",
                    object_id,
                )

        return [
            AircraftProperty(
                value_id=r["value_id"],
                object_id=r["object_id"],
                property_def_id=r["property_definition_id"],
                value=r["value"],
                unit="",
                source=r["source_tag"],
                source_detail=r.get("source_detail", ""),
                confidence=r.get("confidence", 1.0),
                version_id=r.get("version_id", ""),
            )
            for r in rows
        ]

    @staticmethod
    def convert_unit(value: float, from_unit: str, to_unit: str) -> float:
        if from_unit == to_unit:
            return value

        from_dim = UNIT_DIMENSIONS.get(from_unit)
        to_dim = UNIT_DIMENSIONS.get(to_unit)

        if from_dim != to_dim:
            raise ValueError(f"Incompatible unit dimensions: {from_unit} ({from_dim}) vs {to_unit} ({to_dim})")

        key = (from_unit, to_unit)
        if key in UNIT_CONVERSIONS:
            return value * UNIT_CONVERSIONS[key]

        reverse_key = (to_unit, from_unit)
        if reverse_key in UNIT_CONVERSIONS:
            return value / UNIT_CONVERSIONS[reverse_key]

        raise ValueError(f"No conversion available from {from_unit} to {to_unit}")

    @staticmethod
    async def recalculate_derived(property_def_id: str, pool) -> list[AircraftProperty]:
        prop_def = await PropertyService.get_property_definition(property_def_id, pool)
        if prop_def is None or prop_def.derivation_formula is None:
            return []

        return []