"""AeroForge-X v6.0 ConfigurationManagerService

Manages Block/SN level aircraft configuration lifecycle: creation, inheritance,
hierarchy navigation, and conflict detection.
REQ-CFG-001~006
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ConfigViewType(str, Enum):
    DESIGN = "Design"
    MANUFACTURING = "Manufacturing"
    OPERATIONAL = "Operational"


class ConflictType(str, Enum):
    OVERLAPPING_CHANGES = "OverlappingChanges"
    INCOMPATIBLE_VALUES = "IncompatibleValues"
    MISSING_DEPENDENCY = "MissingDependency"


@dataclass
class ConfigurationItem:
    item_id: str
    item_name: str
    item_type: str
    value: dict
    version: int = 1
    source_view: ConfigViewType = ConfigViewType.DESIGN

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "item_name": self.item_name,
            "item_type": self.item_type,
            "value": self.value,
            "version": self.version,
            "source_view": self.source_view.value,
        }


@dataclass
class DesignConfiguration:
    config_id: str
    configuration_items: list[ConfigurationItem] = field(default_factory=list)
    version: int = 1
    status: str = "Active"

    def to_dict(self) -> dict:
        return {
            "config_id": self.config_id,
            "configuration_items": [i.to_dict() for i in self.configuration_items],
            "version": self.version,
            "status": self.status,
        }


@dataclass
class ManufacturingConfiguration:
    config_id: str
    source_design_config_id: str
    manufacturing_rules_applied: list[str] = field(default_factory=list)
    configuration_items: list[ConfigurationItem] = field(default_factory=list)
    version: int = 1
    status: str = "Active"

    def to_dict(self) -> dict:
        return {
            "config_id": self.config_id,
            "source_design_config_id": self.source_design_config_id,
            "manufacturing_rules_applied": self.manufacturing_rules_applied,
            "configuration_items": [i.to_dict() for i in self.configuration_items],
            "version": self.version,
            "status": self.status,
        }


@dataclass
class OperationalConfiguration:
    config_id: str
    source_mfg_config_id: str
    operational_rules_applied: list[str] = field(default_factory=list)
    configuration_items: list[ConfigurationItem] = field(default_factory=list)
    version: int = 1
    status: str = "Active"

    def to_dict(self) -> dict:
        return {
            "config_id": self.config_id,
            "source_mfg_config_id": self.source_mfg_config_id,
            "operational_rules_applied": self.operational_rules_applied,
            "configuration_items": [i.to_dict() for i in self.configuration_items],
            "version": self.version,
            "status": self.status,
        }


@dataclass
class BlockConfiguration:
    block_id: str
    aircraft_type: str
    block_name: str
    design_config: Optional[DesignConfiguration] = None
    manufacturing_config: Optional[ManufacturingConfiguration] = None
    operational_config: Optional[OperationalConfiguration] = None
    locked: bool = False

    def to_dict(self) -> dict:
        return {
            "block_id": self.block_id,
            "aircraft_type": self.aircraft_type,
            "block_name": self.block_name,
            "design_config": self.design_config.to_dict() if self.design_config else None,
            "manufacturing_config": self.manufacturing_config.to_dict() if self.manufacturing_config else None,
            "operational_config": self.operational_config.to_dict() if self.operational_config else None,
            "locked": self.locked,
        }


@dataclass
class SNModification:
    modification_type: str
    item_id: str
    new_values: dict
    reason: str


@dataclass
class SerialNumberConfiguration:
    sn_id: str
    tail_number: str
    block_id: str
    design_config: Optional[DesignConfiguration] = None
    manufacturing_config: Optional[ManufacturingConfiguration] = None
    operational_config: Optional[OperationalConfiguration] = None
    sn_modifications: list[SNModification] = field(default_factory=list)
    service_bulletins: list[dict] = field(default_factory=list)
    repair_alterations: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "sn_id": self.sn_id,
            "tail_number": self.tail_number,
            "block_id": self.block_id,
            "design_config": self.design_config.to_dict() if self.design_config else None,
            "manufacturing_config": self.manufacturing_config.to_dict() if self.manufacturing_config else None,
            "operational_config": self.operational_config.to_dict() if self.operational_config else None,
            "sn_modifications": [
                {
                    "modification_type": m.modification_type,
                    "item_id": m.item_id,
                    "new_values": m.new_values,
                    "reason": m.reason,
                }
                for m in self.sn_modifications
            ],
            "service_bulletins": self.service_bulletins,
            "repair_alterations": self.repair_alterations,
        }


@dataclass
class ConfigurationHierarchy:
    aircraft_type: str
    blocks: list[BlockConfiguration] = field(default_factory=list)
    total_serial_numbers: int = 0

    def to_dict(self) -> dict:
        return {
            "aircraft_type": self.aircraft_type,
            "blocks": [b.to_dict() for b in self.blocks],
            "total_serial_numbers": self.total_serial_numbers,
        }


@dataclass
class ConflictEntry:
    conflict_type: ConflictType
    item_id: str
    block_value: dict
    sn_value: dict
    resolution_suggestion: str


@dataclass
class ConflictResolutionReport:
    block_id: str
    sn_id: str
    conflicts: list[ConflictEntry] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "block_id": self.block_id,
            "sn_id": self.sn_id,
            "conflicts": [
                {
                    "conflict_type": c.conflict_type.value,
                    "item_id": c.item_id,
                    "block_value": c.block_value,
                    "sn_value": c.sn_value,
                    "resolution_suggestion": c.resolution_suggestion,
                }
                for c in self.conflicts
            ],
        }


class ConfigurationManagerService:

    def __init__(self, repo=None) -> None:
        self._repo = repo
        self._blocks: dict[str, BlockConfiguration] = {}
        self._sns: dict[str, SerialNumberConfiguration] = {}
        self._hierarchies: dict[str, ConfigurationHierarchy] = {}

    async def _persist_block(self, block: BlockConfiguration) -> None:
        if self._repo is None:
            return
        await self._repo.save_block({
            "block_id": block.block_id,
            "aircraft_type": block.aircraft_type,
            "block_name": block.block_name,
            "design_config_id": block.design_config.config_id if block.design_config else None,
            "manufacturing_config_id": block.manufacturing_config.config_id if block.manufacturing_config else None,
            "operational_config_id": block.operational_config.config_id if block.operational_config else None,
            "locked": block.locked,
        })

    async def _persist_sn(self, sn: SerialNumberConfiguration) -> None:
        if self._repo is None:
            return
        await self._repo.save_sn({
            "sn_id": sn.sn_id,
            "tail_number": sn.tail_number,
            "block_id": sn.block_id,
            "design_config_id": sn.design_config.config_id if sn.design_config else None,
            "manufacturing_config_id": sn.manufacturing_config.config_id if sn.manufacturing_config else None,
            "operational_config_id": sn.operational_config.config_id if sn.operational_config else None,
            "sn_modifications": [
                {"modification_type": m.modification_type, "item_id": m.item_id,
                 "new_values": m.new_values, "reason": m.reason}
                for m in sn.sn_modifications
            ],
            "service_bulletins": sn.service_bulletins,
            "repair_alterations": sn.repair_alterations,
        })

    async def createBlockConfig(
        self, aircraft_type: str, block_name: str
    ) -> BlockConfiguration:
        block_id = f"BLK-{aircraft_type}-{block_name}"
        if block_id in self._blocks:
            raise ValueError(f"Block configuration already exists: {block_id}")

        design_config = DesignConfiguration(
            config_id=f"DC-{block_id}-1",
            configuration_items=[],
            version=1,
            status="Active",
        )
        block = BlockConfiguration(
            block_id=block_id,
            aircraft_type=aircraft_type,
            block_name=block_name,
            design_config=design_config,
        )
        await self._persist_block(block)
        self._blocks[block_id] = block

        if aircraft_type not in self._hierarchies:
            self._hierarchies[aircraft_type] = ConfigurationHierarchy(
                aircraft_type=aircraft_type
            )
        self._hierarchies[aircraft_type].blocks.append(block)

        return block

    async def createSNConfig(
        self, block_id: str, tail_number: str
    ) -> SerialNumberConfiguration:
        if block_id not in self._blocks:
            raise ValueError(f"Block configuration not found: {block_id}")

        sn_id = f"SN-{tail_number}"
        if sn_id in self._sns:
            raise ValueError(f"SN configuration already exists: {sn_id}")

        block = self._blocks[block_id]
        sn = SerialNumberConfiguration(
            sn_id=sn_id,
            tail_number=tail_number,
            block_id=block_id,
        )
        if block.design_config:
            sn.design_config = DesignConfiguration(
                config_id=f"DC-{sn_id}-1",
                configuration_items=[
                    ConfigurationItem(
                        item_id=i.item_id,
                        item_name=i.item_name,
                        item_type=i.item_type,
                        value=dict(i.value),
                        version=i.version,
                        source_view=i.source_view,
                    )
                    for i in block.design_config.configuration_items
                ],
                version=1,
                status="Active",
            )
        await self._persist_sn(sn)
        self._sns[sn_id] = sn
        self._hierarchies[block.aircraft_type].total_serial_numbers += 1

        return sn

    async def getConfigHierarchy(self, aircraft_type: str) -> ConfigurationHierarchy:
        if aircraft_type in self._hierarchies:
            return self._hierarchies[aircraft_type]
        if self._repo is not None:
            blocks_data = await self._repo.list_blocks_by_aircraft_type(aircraft_type)
            if blocks_data:
                hierarchy = ConfigurationHierarchy(aircraft_type=aircraft_type)
                for bd in blocks_data:
                    block = self._block_from_dict(bd)
                    self._blocks[block.block_id] = block
                    hierarchy.blocks.append(block)
                    sns_data = await self._repo.list_sns_by_block(block.block_id)
                    for sd in sns_data:
                        sn = self._sn_from_dict(sd)
                        self._sns[sn.sn_id] = sn
                    hierarchy.total_serial_numbers += len(sns_data)
                self._hierarchies[aircraft_type] = hierarchy
                return hierarchy
        raise ValueError(f"Aircraft type not found: {aircraft_type}")

    async def inheritBlockConfig(
        self, new_block_name: str, source_block_id: str, changes: dict
    ) -> BlockConfiguration:
        if source_block_id not in self._blocks:
            raise ValueError(f"Source block not found: {source_block_id}")

        source = self._blocks[source_block_id]
        new_block = await self.createBlockConfig(source.aircraft_type, new_block_name)

        if source.design_config:
            new_items = [
                ConfigurationItem(
                    item_id=i.item_id,
                    item_name=i.item_name,
                    item_type=i.item_type,
                    value=dict(i.value),
                    version=i.version,
                    source_view=i.source_view,
                )
                for i in source.design_config.configuration_items
            ]
            for item_id, change_vals in changes.items():
                for item in new_items:
                    if item.item_id == item_id:
                        item.value.update(change_vals)
                        item.version += 1
                        break
            new_block.design_config = DesignConfiguration(
                config_id=f"DC-{new_block.block_id}-1",
                configuration_items=new_items,
                version=1,
                status="Active",
            )
            await self._persist_block(new_block)

        return new_block

    async def inheritSNConfig(
        self, new_sn_id: str, block_id: str, modifications: dict
    ) -> SerialNumberConfiguration:
        if block_id not in self._blocks:
            raise ValueError(f"Block not found: {block_id}")

        block = self._blocks[block_id]
        tail_number = new_sn_id.replace("SN-", "")
        sn = await self.createSNConfig(block_id, tail_number)

        for item_id, mod_vals in modifications.items():
            if sn.design_config:
                for item in sn.design_config.configuration_items:
                    if item.item_id == item_id:
                        item.value.update(mod_vals)
                        item.version += 1
                        sn.sn_modifications.append(
                            SNModification(
                                modification_type="Update",
                                item_id=item_id,
                                new_values=mod_vals,
                                reason="SN-specific modification",
                            )
                        )
                        break
        await self._persist_sn(sn)

        return sn

    async def detectConfigConflicts(
        self, block_id: str, sn_id: str
    ) -> ConflictResolutionReport:
        block = await self.getBlock(block_id)
        if block is None:
            raise ValueError(f"Block not found: {block_id}")
        sn = await self.getSN(sn_id)
        if sn is None:
            raise ValueError(f"SN not found: {sn_id}")
        report = ConflictResolutionReport(block_id=block_id, sn_id=sn_id)

        if not block.design_config or not sn.design_config:
            return report

        block_items = {
            i.item_id: i for i in block.design_config.configuration_items
        }
        sn_items = {i.item_id: i for i in sn.design_config.configuration_items}

        for item_id in set(block_items.keys()) & set(sn_items.keys()):
            b_item = block_items[item_id]
            s_item = sn_items[item_id]
            if b_item.value != s_item.value:
                report.conflicts.append(
                    ConflictEntry(
                        conflict_type=ConflictType.INCOMPATIBLE_VALUES,
                        item_id=item_id,
                        block_value=b_item.value,
                        sn_value=s_item.value,
                        resolution_suggestion=f"Resolve {item_id}: choose block value or SN value",
                    )
                )

        return report

    def _block_from_dict(self, data: dict) -> BlockConfiguration:
        block = BlockConfiguration(
            block_id=data["block_id"],
            aircraft_type=data.get("aircraft_type", ""),
            block_name=data.get("block_name", ""),
            locked=data.get("locked", False),
        )
        if data.get("design_config_id"):
            block.design_config = DesignConfiguration(
                config_id=data["design_config_id"], version=1, status="Active"
            )
        if data.get("manufacturing_config_id"):
            block.manufacturing_config = ManufacturingConfiguration(
                config_id=data["manufacturing_config_id"],
                source_design_config_id=data.get("design_config_id", ""),
                version=1, status="Active",
            )
        if data.get("operational_config_id"):
            block.operational_config = OperationalConfiguration(
                config_id=data["operational_config_id"],
                source_mfg_config_id=data.get("manufacturing_config_id", ""),
                version=1, status="Active",
            )
        return block

    def _sn_from_dict(self, data: dict) -> SerialNumberConfiguration:
        sn = SerialNumberConfiguration(
            sn_id=data["sn_id"],
            tail_number=data.get("tail_number", ""),
            block_id=data.get("block_id", ""),
        )
        if data.get("design_config_id"):
            sn.design_config = DesignConfiguration(
                config_id=data["design_config_id"], version=1, status="Active"
            )
        if data.get("manufacturing_config_id"):
            sn.manufacturing_config = ManufacturingConfiguration(
                config_id=data["manufacturing_config_id"],
                source_design_config_id=data.get("design_config_id", ""),
                version=1, status="Active",
            )
        if data.get("operational_config_id"):
            sn.operational_config = OperationalConfiguration(
                config_id=data["operational_config_id"],
                source_mfg_config_id=data.get("manufacturing_config_id", ""),
                version=1, status="Active",
            )
        for mod_data in data.get("sn_modifications", []):
            if isinstance(mod_data, dict):
                sn.sn_modifications.append(SNModification(
                    modification_type=mod_data.get("modification_type", ""),
                    item_id=mod_data.get("item_id", ""),
                    new_values=mod_data.get("new_values", {}),
                    reason=mod_data.get("reason", ""),
                ))
        sn.service_bulletins = data.get("service_bulletins", [])
        sn.repair_alterations = data.get("repair_alterations", [])
        return sn

    async def getBlock(self, block_id: str) -> Optional[BlockConfiguration]:
        if block_id in self._blocks:
            return self._blocks[block_id]
        if self._repo is not None:
            data = await self._repo.get_block(block_id)
            if data is not None:
                block = self._block_from_dict(data)
                self._blocks[block_id] = block
                return block
        return None

    async def getSN(self, sn_id: str) -> Optional[SerialNumberConfiguration]:
        if sn_id in self._sns:
            return self._sns[sn_id]
        if self._repo is not None:
            data = await self._repo.get_sn(sn_id)
            if data is not None:
                sn = self._sn_from_dict(data)
                self._sns[sn_id] = sn
                return sn
        return None

    def invalidate_cache(self, aircraft_type: str | None = None, block_id: str | None = None) -> None:
        if aircraft_type is not None:
            self._hierarchies.pop(aircraft_type, None)
        else:
            self._hierarchies.clear()
        if block_id is not None:
            self._blocks.pop(block_id, None)
            # Also remove SNs belonging to this block
            sn_ids_to_remove = [sid for sid, sn in self._sns.items() if hasattr(sn, 'block_id') and sn.block_id == block_id]
            for sid in sn_ids_to_remove:
                del self._sns[sid]
        else:
            self._blocks.clear()
            self._sns.clear()