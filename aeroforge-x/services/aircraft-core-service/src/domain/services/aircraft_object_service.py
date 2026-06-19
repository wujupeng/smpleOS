from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from src.domain.entities.aircraft_object import AircraftObject
from src.domain.entities.aircraft_object_version import AircraftObjectVersion
from src.domain.enums import BaselineType, LifecycleState, ObjectType
from src.domain.value_objects.aircraft_object_link import AircraftObjectLink
from src.domain.value_objects.aircraft_property import AircraftProperty


class AircraftObjectService:

    @staticmethod
    async def create_object(
        object_type: ObjectType,
        name: str,
        initial_properties: list[dict] | None = None,
        parent_object_id: str | None = None,
    ) -> AircraftObject:
        obj = AircraftObject(object_type=object_type, name=name)
        obj.generate_id()
        if initial_properties:
            for prop_data in initial_properties:
                prop = AircraftProperty(
                    value_id=str(uuid.uuid4()),
                    object_id=obj.id,
                    property_def_id=prop_data.get("property_def_id", ""),
                    value=prop_data.get("value"),
                    unit=prop_data.get("unit", ""),
                    source=prop_data.get("source", "DesignValue"),
                    source_detail=prop_data.get("source_detail", ""),
                    confidence=prop_data.get("confidence", 1.0),
                )
                obj.add_property(prop)
        return obj

    @staticmethod
    async def get_object_by_id(object_id: str, pool) -> AircraftObject | None:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM aircraft_core.aircraft_objects WHERE id = $1", object_id
            )
            if row is None:
                return None
            return AircraftObject(
                id=row["id"],
                object_type=row["object_type"],
                name=row["name"],
                lifecycle_state=row["lifecycle_state"],
                design_data=row["design_data"],
                manufacturing_data=row["manufacturing_data"],
                operation_data=row["operation_data"],
                certification_data=row["certification_data"],
                optimistic_lock_version=row["optimistic_lock_version"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    @staticmethod
    async def update_object(
        object_id: str,
        change_summary: str,
        author: str,
        data_updates: dict[str, Any] | None = None,
        pool=None,
    ) -> AircraftObjectVersion | None:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM aircraft_core.aircraft_objects WHERE id = $1", object_id
            )
            if row is None:
                return None

            current_version = row["optimistic_lock_version"]
            update_fields = []
            update_values = []
            param_idx = 1

            if data_updates:
                for field_name in ("design_data", "manufacturing_data", "operation_data", "certification_data"):
                    if field_name in data_updates:
                        param_idx += 1
                        update_fields.append(f"{field_name} = ${param_idx}")
                        update_values.append(data_updates[field_name])

            param_idx += 1
            update_fields.append(f"optimistic_lock_version = {current_version} + 1")
            param_idx += 1
            update_fields.append(f"updated_at = NOW()")

            param_idx += 1
            update_values.append(current_version)
            result = await conn.fetchrow(
                f"UPDATE aircraft_core.aircraft_objects SET {', '.join(update_fields)} "
                f"WHERE id = ${param_idx} AND optimistic_lock_version = ${param_idx + 1} "
                f"RETURNING *",
                *update_values, object_id, current_version
            )
            if result is None:
                raise ValueError("Optimistic lock conflict: object was modified by another transaction")

            version_number = await conn.fetchval(
                "SELECT COALESCE(MAX(version_number), 0) + 1 FROM aircraft_core.aircraft_object_versions WHERE object_id = $1",
                object_id,
            )
            version_id = f"AVER-{object_id}-{version_number}"
            await conn.execute(
                "INSERT INTO aircraft_core.aircraft_object_versions (version_id, object_id, version_number, snapshot, change_summary, author) "
                "VALUES ($1, $2, $3, $4, $5, $6)",
                version_id, object_id, version_number,
                dict(result), change_summary, author,
            )
            return AircraftObjectVersion(
                version_id=version_id,
                object_id=object_id,
                version_number=version_number,
                snapshot=dict(result),
                change_summary=change_summary,
                author=author,
            )

    @staticmethod
    async def delete_object(object_id: str, pool) -> bool:
        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM aircraft_core.aircraft_objects WHERE id = $1", object_id
            )
            return result == "DELETE 1"

    @staticmethod
    async def transition_lifecycle(
        object_id: str,
        target_state: LifecycleState,
        validation_data: dict[str, bool] | None = None,
        force: bool = False,
        pool=None,
    ) -> AircraftObject | None:
        obj = await AircraftObjectService.get_object_by_id(object_id, pool)
        if obj is None:
            return None
        if force:
            obj.lifecycle_state = target_state
            obj.updated_at = datetime.utcnow()
        else:
            obj.transition_to(target_state, validation_data)

        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE aircraft_core.aircraft_objects SET lifecycle_state = $1, updated_at = NOW() WHERE id = $2",
                obj.lifecycle_state.value, object_id,
            )
        return obj