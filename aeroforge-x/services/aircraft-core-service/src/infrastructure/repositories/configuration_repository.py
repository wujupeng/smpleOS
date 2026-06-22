"""AeroForge-X Configuration Repository

Persistence layer for ConfigurationManagerService + ConfigurationBaselineService.
Target tables: block_configurations, serial_number_configurations, configuration_baselines

Design rules:
- version field is ALWAYS managed by the database (version = version + 1)
- Business layer MUST NOT pass version in updates dict
- save_block() is for INSERT only (first creation, ON CONFLICT DO NOTHING)
- update_block() is for UPDATE with optional optimistic locking
- Only update_block(expected_version=) increments version
- save_block() NEVER changes version — it is create-only
"""

from __future__ import annotations

from typing import Any, Optional

from src.infrastructure.repositories.base_repository import (
    AsyncpgRepository,
    InMemoryRepository,
)

_BLOCK_UPDATABLE_COLUMNS = frozenset({
    "aircraft_type", "block_name", "design_config_id",
    "manufacturing_config_id", "operational_config_id", "locked",
})

_SN_UPDATABLE_COLUMNS = frozenset({
    "tail_number", "block_id", "design_config_id",
    "manufacturing_config_id", "operational_config_id",
})

_SN_JSONB_COLUMNS = frozenset({
    "sn_modifications", "service_bulletins", "repair_alterations",
})

_PROTECTED_COLUMNS = frozenset({
    "block_id", "version", "created_at", "updated_at",
})


class VersionConflictError(Exception):
    pass


class ProtectedColumnError(Exception):
    pass


class ConfigurationRepository(InMemoryRepository):

    async def save_block(self, block: dict) -> None:
        self._put("block_configurations", block["block_id"], block)

    async def get_block(self, block_id: str) -> Optional[dict]:
        return self._get("block_configurations", block_id)

    async def list_blocks_by_aircraft_type(self, aircraft_type: str) -> list[dict]:
        return self._list("block_configurations", aircraft_type=aircraft_type)

    async def save_sn(self, sn: dict) -> None:
        self._put("serial_number_configurations", sn["sn_id"], sn)

    async def get_sn(self, sn_id: str) -> Optional[dict]:
        return self._get("serial_number_configurations", sn_id)

    async def list_sns_by_block(self, block_id: str) -> list[dict]:
        return self._list("serial_number_configurations", block_id=block_id)

    async def save_baseline(self, baseline: dict) -> None:
        self._put("configuration_baselines", baseline["baseline_id"], baseline)

    async def get_baseline(self, baseline_id: str) -> Optional[dict]:
        return self._get("configuration_baselines", baseline_id)

    async def list_baselines_by_block(self, block_id: str) -> list[dict]:
        return self._list("configuration_baselines", block_id=block_id)

    async def update_block(self, block_id: str, updates: dict, expected_version: int | None = None) -> bool:
        existing = self._get("block_configurations", block_id)
        if existing is None:
            return False
        protected = set(updates.keys()) & _PROTECTED_COLUMNS
        if protected:
            raise ProtectedColumnError(
                f"Cannot modify protected columns: {protected}. "
                f"Use expected_version for optimistic locking."
            )
        if expected_version is not None and existing.get("version", 0) != expected_version:
            raise VersionConflictError(
                f"Version conflict for block {block_id}: "
                f"expected {expected_version}, actual {existing.get('version', 0)}"
            )
        for k, v in updates.items():
            if k in _BLOCK_UPDATABLE_COLUMNS:
                existing[k] = v
        if expected_version is not None:
            existing["version"] = existing.get("version", 0) + 1
        self._put("block_configurations", block_id, existing)
        return True

    async def update_sn(self, sn_id: str, updates: dict) -> bool:
        existing = self._get("serial_number_configurations", sn_id)
        if existing is None:
            return False
        existing.update(updates)
        self._put("serial_number_configurations", sn_id, existing)
        return True


class AsyncpgConfigurationRepository(AsyncpgRepository):

    async def save_block(self, block: dict) -> None:
        await self._execute(
            """
            INSERT INTO block_configurations
                (block_id, aircraft_type, block_name, design_config_id,
                 manufacturing_config_id, operational_config_id, locked)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (block_id) DO NOTHING
            """,
            block["block_id"],
            block["aircraft_type"],
            block["block_name"],
            block.get("design_config_id"),
            block.get("manufacturing_config_id"),
            block.get("operational_config_id"),
            block.get("locked", False),
        )

    async def get_block(self, block_id: str) -> Optional[dict]:
        row = await self._fetchrow(
            "SELECT * FROM block_configurations WHERE block_id = $1", block_id
        )
        return dict(row) if row else None

    async def list_blocks_by_aircraft_type(self, aircraft_type: str) -> list[dict]:
        rows = await self._fetch(
            "SELECT * FROM block_configurations WHERE aircraft_type = $1 ORDER BY block_name",
            aircraft_type,
        )
        return [dict(r) for r in rows]

    async def save_sn(self, sn: dict) -> None:
        await self._execute(
            """
            INSERT INTO serial_number_configurations
                (sn_id, tail_number, block_id, design_config_id,
                 manufacturing_config_id, operational_config_id,
                 sn_modifications, service_bulletins, repair_alterations)
            VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8::jsonb, $9::jsonb)
            ON CONFLICT (sn_id) DO UPDATE SET
                tail_number = EXCLUDED.tail_number,
                block_id = EXCLUDED.block_id,
                design_config_id = EXCLUDED.design_config_id,
                manufacturing_config_id = EXCLUDED.manufacturing_config_id,
                operational_config_id = EXCLUDED.operational_config_id,
                sn_modifications = EXCLUDED.sn_modifications,
                service_bulletins = EXCLUDED.service_bulletins,
                repair_alterations = EXCLUDED.repair_alterations
            """,
            sn["sn_id"],
            sn["tail_number"],
            sn["block_id"],
            sn.get("design_config_id"),
            sn.get("manufacturing_config_id"),
            sn.get("operational_config_id"),
            self._json_dumps(sn.get("sn_modifications", [])),
            self._json_dumps(sn.get("service_bulletins", [])),
            self._json_dumps(sn.get("repair_alterations", [])),
        )

    async def get_sn(self, sn_id: str) -> Optional[dict]:
        row = await self._fetchrow(
            "SELECT * FROM serial_number_configurations WHERE sn_id = $1", sn_id
        )
        if row is None:
            return None
        result = dict(row)
        for key in _SN_JSONB_COLUMNS:
            result[key] = self._json_loads(result.get(key, "[]"))
        return result

    async def list_sns_by_block(self, block_id: str) -> list[dict]:
        rows = await self._fetch(
            "SELECT * FROM serial_number_configurations WHERE block_id = $1 ORDER BY tail_number",
            block_id,
        )
        results = []
        for r in rows:
            d = dict(r)
            for key in _SN_JSONB_COLUMNS:
                d[key] = self._json_loads(d.get(key, "[]"))
            results.append(d)
        return results

    async def save_baseline(self, baseline: dict) -> None:
        await self._execute(
            """
            INSERT INTO configuration_baselines
                (baseline_id, baseline_type, block_id, configuration_snapshot,
                 frozen_items, milestone, established_by, locked)
            VALUES ($1, $2, $3, $4::jsonb, $5::jsonb, $6, $7, $8)
            ON CONFLICT (baseline_id) DO UPDATE SET
                configuration_snapshot = EXCLUDED.configuration_snapshot,
                frozen_items = EXCLUDED.frozen_items,
                milestone = EXCLUDED.milestone,
                locked = EXCLUDED.locked
            """,
            baseline["baseline_id"],
            baseline["baseline_type"],
            baseline["block_id"],
            self._json_dumps(baseline.get("configuration_snapshot", {})),
            self._json_dumps(baseline.get("frozen_items", [])),
            baseline["milestone"],
            baseline["established_by"],
            baseline.get("locked", True),
        )

    async def get_baseline(self, baseline_id: str) -> Optional[dict]:
        row = await self._fetchrow(
            "SELECT * FROM configuration_baselines WHERE baseline_id = $1",
            baseline_id,
        )
        if row is None:
            return None
        result = dict(row)
        result["configuration_snapshot"] = self._json_loads(
            result.get("configuration_snapshot", "{}")
        )
        result["frozen_items"] = self._json_loads(result.get("frozen_items", "[]"))
        return result

    async def list_baselines_by_block(self, block_id: str) -> list[dict]:
        rows = await self._fetch(
            "SELECT * FROM configuration_baselines WHERE block_id = $1 ORDER BY established_at DESC",
            block_id,
        )
        results = []
        for r in rows:
            d = dict(r)
            d["configuration_snapshot"] = self._json_loads(
                d.get("configuration_snapshot", "{}")
            )
            d["frozen_items"] = self._json_loads(d.get("frozen_items", "[]"))
            results.append(d)
        return results

    async def update_block(self, block_id: str, updates: dict, expected_version: int | None = None) -> bool:
        protected = set(updates.keys()) & _PROTECTED_COLUMNS
        if protected:
            raise ProtectedColumnError(
                f"Cannot modify protected columns: {protected}. "
                f"Use expected_version for optimistic locking."
            )

        filtered = {k: v for k, v in updates.items() if k in _BLOCK_UPDATABLE_COLUMNS}
        if not filtered:
            return False

        set_parts = [f"{col} = ${i}" for i, col in enumerate(filtered.keys(), start=1)]
        args = list(filtered.values())

        if expected_version is not None:
            set_parts.append("version = version + 1")
            set_parts.append("updated_at = NOW()")
            args.append(block_id)
            args.append(expected_version)
            idx_pk = len(args) - 1
            idx_ver = len(args)
            result = await self._execute(
                f"UPDATE block_configurations SET {', '.join(set_parts)} "
                f"WHERE block_id = ${idx_pk} AND version = ${idx_ver}",
                *args,
            )
            if "UPDATE 0" in result:
                raise VersionConflictError(
                    f"Version conflict for block {block_id}: expected {expected_version}"
                )
        else:
            set_parts.append("updated_at = NOW()")
            args.append(block_id)
            idx_pk = len(args)
            result = await self._execute(
                f"UPDATE block_configurations SET {', '.join(set_parts)} "
                f"WHERE block_id = ${idx_pk}",
                *args,
            )
        return "UPDATE 1" in result

    async def update_sn(self, sn_id: str, updates: dict) -> bool:
        filtered = {}
        jsonb_filtered = {}
        for k, v in updates.items():
            if k in _SN_UPDATABLE_COLUMNS:
                filtered[k] = v
            elif k in _SN_JSONB_COLUMNS:
                jsonb_filtered[k] = v

        set_parts = []
        args = []
        idx = 1
        for col, val in filtered.items():
            set_parts.append(f"{col} = ${idx}")
            args.append(val)
            idx += 1
        for col, val in jsonb_filtered.items():
            set_parts.append(f"{col} = ${idx}::jsonb")
            args.append(self._json_dumps(val))
            idx += 1

        if not set_parts:
            return False
        args.append(sn_id)
        result = await self._execute(
            f"UPDATE serial_number_configurations SET {', '.join(set_parts)} WHERE sn_id = ${idx}",
            *args,
        )
        return "UPDATE 1" in result