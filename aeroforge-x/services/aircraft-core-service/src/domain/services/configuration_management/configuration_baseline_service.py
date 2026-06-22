"""AeroForge-X v6.0 ConfigurationBaselineService

Manages configuration baselines (FBL/FCL/FSDL): establishment, freezing,
change tracking, and baseline comparison.
REQ-CFG-012~017
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .configuration_manager_service import BlockConfiguration


class BaselineType(str, Enum):
    FBL = "FBL"
    FCL = "FCL"
    FSDL = "FSDL"


class BaselineMilestone(str, Enum):
    SRR = "SRR"
    PDR = "PDR"
    CDR = "CDR"


@dataclass
class BaselineChangeRecord:
    change_id: str
    baseline_id: str
    change_request_id: str
    change_type: str
    approver: str
    approved_at: str
    affected_items: list[str] = field(default_factory=list)


@dataclass
class ConfigurationBaseline:
    baseline_id: str
    baseline_type: BaselineType
    block_id: str
    configuration_snapshot: dict
    frozen_items: list[str] = field(default_factory=list)
    milestone: str = ""
    established_by: str = ""
    locked: bool = True
    established_at: str = ""
    change_history: list[BaselineChangeRecord] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "baseline_id": self.baseline_id,
            "baseline_type": self.baseline_type.value,
            "block_id": self.block_id,
            "configuration_snapshot": self.configuration_snapshot,
            "frozen_items": self.frozen_items,
            "milestone": self.milestone,
            "established_by": self.established_by,
            "locked": self.locked,
            "established_at": self.established_at,
            "change_history": [
                {
                    "change_id": c.change_id,
                    "baseline_id": c.baseline_id,
                    "change_request_id": c.change_request_id,
                    "change_type": c.change_type,
                    "approver": c.approver,
                    "approved_at": c.approved_at,
                    "affected_items": c.affected_items,
                }
                for c in self.change_history
            ],
        }


@dataclass
class BaselineDeltaItem:
    item_id: str
    delta_type: str
    baseline1_value: Optional[dict]
    baseline2_value: Optional[dict]


@dataclass
class BaselineDeltaReport:
    baseline_id_1: str
    baseline_id_2: str
    added_items: list[str] = field(default_factory=list)
    removed_items: list[str] = field(default_factory=list)
    modified_items: list[BaselineDeltaItem] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "baseline_id_1": self.baseline_id_1,
            "baseline_id_2": self.baseline_id_2,
            "added_items": self.added_items,
            "removed_items": self.removed_items,
            "modified_items": [
                {
                    "item_id": m.item_id,
                    "delta_type": m.delta_type,
                    "baseline1_value": m.baseline1_value,
                    "baseline2_value": m.baseline2_value,
                }
                for m in self.modified_items
            ],
        }


class ConfigurationBaselineService:

    def __init__(self, repo=None) -> None:
        self._repo = repo
        self._baselines: dict[str, ConfigurationBaseline] = {}

    async def _persist_baseline(self, baseline: ConfigurationBaseline) -> None:
        if self._repo is None:
            return
        await self._repo.save_baseline({
            "baseline_id": baseline.baseline_id,
            "baseline_type": baseline.baseline_type.value,
            "block_id": baseline.block_id,
            "configuration_snapshot": baseline.configuration_snapshot,
            "frozen_items": baseline.frozen_items,
            "milestone": baseline.milestone,
            "established_by": baseline.established_by,
            "locked": baseline.locked,
        })

    async def establishFBL(
        self, block: BlockConfiguration, established_by: str
    ) -> ConfigurationBaseline:
        return await self._establish_baseline(
            block, BaselineType.FBL, BaselineMilestone.SRR, established_by
        )

    async def establishFCL(
        self, block: BlockConfiguration, established_by: str
    ) -> ConfigurationBaseline:
        return await self._establish_baseline(
            block, BaselineType.FCL, BaselineMilestone.PDR, established_by
        )

    async def establishFSDL(
        self, block: BlockConfiguration, established_by: str
    ) -> ConfigurationBaseline:
        return await self._establish_baseline(
            block, BaselineType.FSDL, BaselineMilestone.CDR, established_by
        )

    async def _establish_baseline(
        self,
        block: BlockConfiguration,
        baseline_type: BaselineType,
        milestone: BaselineMilestone,
        established_by: str,
    ) -> ConfigurationBaseline:
        baseline_id = f"{baseline_type.value}-{block.block_id}-{uuid.uuid4().hex[:6]}"

        snapshot = block.to_dict()
        frozen_items = []
        if block.design_config:
            frozen_items.extend(
                [i.item_id for i in block.design_config.configuration_items]
            )

        baseline = ConfigurationBaseline(
            baseline_id=baseline_id,
            baseline_type=baseline_type,
            block_id=block.block_id,
            configuration_snapshot=snapshot,
            frozen_items=frozen_items,
            milestone=milestone.value,
            established_by=established_by,
            locked=True,
        )
        self._baselines[baseline_id] = baseline
        block.locked = True
        await self._persist_baseline(baseline)

        return baseline

    async def freezeBaselineItems(self, baseline_id: str) -> ConfigurationBaseline:
        baseline = await self.getBaseline(baseline_id)
        if baseline is None:
            raise ValueError(f"Baseline not found: {baseline_id}")
        baseline.locked = True
        return baseline

    async def trackBaselineChanges(
        self,
        baseline_id: str,
        change_request_id: str,
        change_type: str,
        approver: str,
        affected_items: list[str],
    ) -> BaselineChangeRecord:
        baseline = await self.getBaseline(baseline_id)
        if baseline is None:
            raise ValueError(f"Baseline not found: {baseline_id}")

        record = BaselineChangeRecord(
            change_id=f"BCR-{uuid.uuid4().hex[:8]}",
            baseline_id=baseline_id,
            change_request_id=change_request_id,
            change_type=change_type,
            approver=approver,
            approved_at="",
            affected_items=affected_items,
        )
        baseline.change_history.append(record)
        return record

    async def compareBaselines(
        self, baseline_id_1: str, baseline_id_2: str
    ) -> BaselineDeltaReport:
        b1 = await self.getBaseline(baseline_id_1)
        if b1 is None:
            raise ValueError(f"Baseline not found: {baseline_id_1}")
        b2 = await self.getBaseline(baseline_id_2)
        if b2 is None:
            raise ValueError(f"Baseline not found: {baseline_id_2}")

        report = BaselineDeltaReport(
            baseline_id_1=baseline_id_1,
            baseline_id_2=baseline_id_2,
        )

        items1 = {item: item for item in b1.frozen_items}
        items2 = {item: item for item in b2.frozen_items}

        set1 = set(items1.keys())
        set2 = set(items2.keys())

        report.added_items = list(set2 - set1)
        report.removed_items = list(set1 - set2)

        snapshot1 = b1.configuration_snapshot
        snapshot2 = b2.configuration_snapshot

        if snapshot1 != snapshot2:
            report.modified_items.append(
                BaselineDeltaItem(
                    item_id="snapshot",
                    delta_type="SnapshotModified",
                    baseline1_value=snapshot1,
                    baseline2_value=snapshot2,
                )
            )

        return report

    def _baseline_from_dict(self, data: dict) -> ConfigurationBaseline:
        return ConfigurationBaseline(
            baseline_id=data["baseline_id"],
            baseline_type=BaselineType(data.get("baseline_type", "FBL")),
            block_id=data.get("block_id", ""),
            configuration_snapshot=data.get("configuration_snapshot", {}),
            frozen_items=data.get("frozen_items", []),
            milestone=data.get("milestone", ""),
            established_by=data.get("established_by", ""),
            locked=data.get("locked", True),
            established_at=str(data.get("established_at", "")),
        )

    async def getBaseline(self, baseline_id: str) -> Optional[ConfigurationBaseline]:
        if baseline_id in self._baselines:
            return self._baselines[baseline_id]
        if self._repo is not None:
            data = await self._repo.get_baseline(baseline_id)
            if data is not None:
                baseline = self._baseline_from_dict(data)
                self._baselines[baseline_id] = baseline
                return baseline
        return None

    def invalidate_cache(self, baseline_id: str | None = None) -> None:
        if baseline_id is not None:
            self._baselines.pop(baseline_id, None)
        else:
            self._baselines.clear()