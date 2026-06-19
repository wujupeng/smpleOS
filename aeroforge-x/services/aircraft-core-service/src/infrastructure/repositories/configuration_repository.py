"""AeroForge-X Configuration Repository

Persistence layer for ConfigurationManagerService + ConfigurationBaselineService.
Target tables: block_configurations, serial_number_configurations, configuration_baselines
"""

from __future__ import annotations

from typing import Any, Optional

from src.infrastructure.repositories.base_repository import (
    AsyncpgRepository,
    InMemoryRepository,
)


class ConfigurationRepository(InMemoryRepository):

    def save_block(self, block: dict) -> None:
        self._put("block_configurations", block["block_id"], block)

    def get_block(self, block_id: str) -> Optional[dict]:
        return self._get("block_configurations", block_id)

    def list_blocks_by_aircraft_type(self, aircraft_type: str) -> list[dict]:
        return self._list("block_configurations", aircraft_type=aircraft_type)

    def save_sn(self, sn: dict) -> None:
        self._put("serial_number_configurations", sn["sn_id"], sn)

    def get_sn(self, sn_id: str) -> Optional[dict]:
        return self._get("serial_number_configurations", sn_id)

    def list_sns_by_block(self, block_id: str) -> list[dict]:
        return self._list("serial_number_configurations", block_id=block_id)

    def save_baseline(self, baseline: dict) -> None:
        self._put("configuration_baselines", baseline["baseline_id"], baseline)

    def get_baseline(self, baseline_id: str) -> Optional[dict]:
        return self._get("configuration_baselines", baseline_id)

    def list_baselines_by_block(self, block_id: str) -> list[dict]:
        return self._list("configuration_baselines", block_id=block_id)

    def update_block(self, block_id: str, updates: dict) -> bool:
        existing = self._get("block_configurations", block_id)
        if existing is None:
            return False
        existing.update(updates)
        self._put("block_configurations", block_id, existing)
        return True

    def update_sn(self, sn_id: str, updates: dict) -> bool:
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
            ON CONFLICT (block_id) DO UPDATE SET
                aircraft_type = EXCLUDED.aircraft_type,
                block_name = EXCLUDED.block_name,
                design_config_id = EXCLUDED.design_config_id,
                manufacturing_config_id = EXCLUDED.manufacturing_config_id,
                operational_config_id = EXCLUDED.operational_config_id,
                locked = EXCLUDED.locked,
                updated_at = NOW()
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
        for key in ("sn_modifications", "service_bulletins", "repair_alterations"):
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
            for key in ("sn_modifications", "service_bulletins", "repair_alterations"):
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

    async def update_block(self, block_id: str, updates: dict) -> bool:
        set_clauses = []
        args = []
        idx = 1
        for key, val in updates.items():
            if key == "block_id":
                continue
            set_clauses.append(f"{key} = ${idx}")
            args.append(val)
            idx += 1
        if not set_clauses:
            return False
        set_clauses.append("updated_at = NOW()")
        args.append(block_id)
        result = await self._execute(
            f"UPDATE block_configurations SET {', '.join(set_clauses)} WHERE block_id = ${idx}",
            *args,
        )
        return "UPDATE 1" in result

    async def update_sn(self, sn_id: str, updates: dict) -> bool:
        set_clauses = []
        args = []
        idx = 1
        for key, val in updates.items():
            if key == "sn_id":
                continue
            if key in ("sn_modifications", "service_bulletins", "repair_alterations"):
                set_clauses.append(f"{key} = ${idx}::jsonb")
                args.append(self._json_dumps(val))
            else:
                set_clauses.append(f"{key} = ${idx}")
                args.append(val)
            idx += 1
        if not set_clauses:
            return False
        args.append(sn_id)
        result = await self._execute(
            f"UPDATE serial_number_configurations SET {', '.join(set_clauses)} WHERE sn_id = ${idx}",
            *args,
        )
        return "UPDATE 1" in result