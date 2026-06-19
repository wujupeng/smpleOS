from __future__ import annotations

from typing import Any

from src.domain.entities.aircraft_object_version import AircraftObjectVersion
from src.domain.enums import BaselineType


class VersionService:

    @staticmethod
    async def get_version_history(object_id: str, pool) -> list[AircraftObjectVersion]:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM aircraft_core.aircraft_object_versions WHERE object_id = $1 ORDER BY version_number",
                object_id,
            )
            return [AircraftObjectVersion(**dict(r)) for r in rows]

    @staticmethod
    async def get_version(object_id: str, version_number: int, pool) -> AircraftObjectVersion | None:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM aircraft_core.aircraft_object_versions WHERE object_id = $1 AND version_number = $2",
                object_id, version_number,
            )
            if row is None:
                return None
            return AircraftObjectVersion(**dict(row))

    @staticmethod
    async def diff_versions(object_id: str, v1: int, v2: int, pool) -> dict[str, Any]:
        ver1 = await VersionService.get_version(object_id, v1, pool)
        ver2 = await VersionService.get_version(object_id, v2, pool)
        if ver1 is None or ver2 is None:
            return {"error": "One or both versions not found"}

        snapshot1 = ver1.snapshot
        snapshot2 = ver2.snapshot
        differences = []

        all_keys = set(list(snapshot1.keys()) + list(snapshot2.keys()))
        for key in all_keys:
            val1 = snapshot1.get(key)
            val2 = snapshot2.get(key)
            if val1 != val2:
                differences.append({
                    "property": key,
                    "old_value": val1,
                    "new_value": val2,
                })

        return {
            "object_id": object_id,
            "version_from": v1,
            "version_to": v2,
            "differences": differences,
            "total_changes": len(differences),
        }

    @staticmethod
    async def create_frozen_baseline(
        object_id: str,
        version_numbers: list[int],
        pool,
    ) -> dict[str, Any]:
        async with pool.acquire() as conn:
            async with conn.transaction():
                for vn in version_numbers:
                    row = await conn.fetchrow(
                        "SELECT * FROM aircraft_core.aircraft_object_versions WHERE object_id = $1 AND version_number = $2",
                        object_id, vn,
                    )
                    if row is None:
                        return {"error": f"Version {vn} not found"}
                    if row["is_frozen"]:
                        return {"error": f"Version {vn} is already frozen"}

                for vn in version_numbers:
                    await conn.execute(
                        "UPDATE aircraft_core.aircraft_object_versions SET baseline_type = $1, is_frozen = TRUE WHERE object_id = $2 AND version_number = $3",
                        BaselineType.Frozen.value, object_id, vn,
                    )

        return {
            "object_id": object_id,
            "baseline_type": "Frozen",
            "version_numbers": version_numbers,
            "status": "created",
        }

    @staticmethod
    async def create_released_baseline(
        object_id: str,
        version_numbers: list[int],
        lifecycle_stage: str,
        pool,
    ) -> dict[str, Any]:
        async with pool.acquire() as conn:
            async with conn.transaction():
                for vn in version_numbers:
                    await conn.execute(
                        "UPDATE aircraft_core.aircraft_object_versions SET baseline_type = $1, is_frozen = TRUE WHERE object_id = $2 AND version_number = $3",
                        BaselineType.Released.value, object_id, vn,
                    )

        return {
            "object_id": object_id,
            "baseline_type": "Released",
            "lifecycle_stage": lifecycle_stage,
            "version_numbers": version_numbers,
            "status": "created",
        }