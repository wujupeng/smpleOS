from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..entities.bom_item import BOMItem, EBOM, MBOM, SBOM

logger = logging.getLogger(__name__)


class DiffType(str, Enum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNMAPPED = "unmapped"


class SyncSuggestion(str, Enum):
    AUTO_SYNC = "auto_sync"
    MANUAL_CONFIRM = "manual_confirm"
    NO_ACTION = "no_action"


@dataclass
class DiffItem:
    item_code: str
    item_name: str
    diff_type: DiffType
    source_bom: str
    target_bom: str
    details: dict[str, Any] = field(default_factory=dict)
    suggestion: SyncSuggestion = SyncSuggestion.MANUAL_CONFIRM

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_code": self.item_code,
            "item_name": self.item_name,
            "diff_type": self.diff_type.value,
            "source_bom": self.source_bom,
            "target_bom": self.target_bom,
            "details": self.details,
            "suggestion": self.suggestion.value,
        }


@dataclass
class ConsistencyReport:
    is_consistent: bool = True
    ebom_item_count: int = 0
    mbom_item_count: int = 0
    sbom_item_count: int = 0
    mapping_completeness: dict[str, Any] = field(default_factory=dict)
    attribute_consistency: dict[str, Any] = field(default_factory=dict)
    diff_items: list[DiffItem] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_consistent": self.is_consistent,
            "ebom_item_count": self.ebom_item_count,
            "mbom_item_count": self.mbom_item_count,
            "sbom_item_count": self.sbom_item_count,
            "mapping_completeness": self.mapping_completeness,
            "attribute_consistency": self.attribute_consistency,
            "diff_items": [d.to_dict() for d in self.diff_items],
            "errors": self.errors,
            "warnings": self.warnings,
        }


class BOMConsistencyChecker:
    def check_consistency(
        self,
        ebom: EBOM,
        mbom: MBOM | None = None,
        sbom: SBOM | None = None,
    ) -> ConsistencyReport:
        report = ConsistencyReport()

        if ebom.root_item is None:
            report.is_consistent = False
            report.errors.append("eBOM has no root item")
            return report

        ebom_items = ebom.root_item.flatten()
        ebom_codes = {i.item_code for i in ebom_items}
        report.ebom_item_count = len(ebom_codes)

        if mbom and mbom.root_item:
            mbom_items = mbom.root_item.flatten()
            mbom_codes = {i.item_code for i in mbom_items}
            mbom_ebom_refs = {i.ebom_item_code for i in mbom_items if i.ebom_item_code}
            report.mbom_item_count = len(mbom_codes)

            ebom_leaf_codes = {i.item_code for i in ebom_items if i.part_type != "assembly"}
            mapped = ebom_leaf_codes & mbom_ebom_refs
            unmapped = ebom_leaf_codes - mbom_ebom_refs

            report.mapping_completeness["ebom_to_mbom"] = {
                "total_ebom_items": len(ebom_leaf_codes),
                "mapped_items": len(mapped),
                "unmapped_items": len(unmapped),
                "completeness_percent": round(len(mapped) / max(len(ebom_leaf_codes), 1) * 100, 1),
            }

            if unmapped:
                report.is_consistent = False
                report.warnings.append(f"{len(unmapped)} eBOM items not mapped to mBOM")

        if sbom and sbom.root_item:
            sbom_items = sbom.root_item.flatten()
            sbom_codes = {i.item_code for i in sbom_items}
            report.sbom_item_count = len(sbom_codes)

            if mbom and mbom.root_item:
                mbom_items = mbom.root_item.flatten()
                mbom_codes = {i.item_code for i in mbom_items}
                sbom_only = sbom_codes - mbom_codes
                mbom_only = mbom_codes - sbom_codes

                report.mapping_completeness["mbom_to_sbom"] = {
                    "total_mbom_items": len(mbom_codes),
                    "total_sbom_items": len(sbom_codes),
                    "sbom_only_items": len(sbom_only),
                    "mbom_only_items": len(mbom_only),
                }

                if sbom_only or mbom_only:
                    report.is_consistent = False

        self._check_attribute_consistency(ebom, mbom, sbom, report)

        return report

    def detect_differences(
        self,
        ebom: EBOM,
        mbom: MBOM | None = None,
        sbom: SBOM | None = None,
    ) -> list[DiffItem]:
        diffs: list[DiffItem] = []

        if ebom.root_item is None:
            return diffs

        ebom_items = ebom.root_item.flatten()
        ebom_codes = {i.item_code for i in ebom_items}
        ebom_map = {i.item_code: i for i in ebom_items}

        if mbom and mbom.root_item:
            mbom_items = mbom.root_item.flatten()
            mbom_ebom_refs = {i.ebom_item_code for i in mbom_items if i.ebom_item_code}
            mbom_codes = {i.item_code for i in mbom_items}

            ebom_leaf_codes = {i.item_code for i in ebom_items if i.part_type != "assembly"}

            for code in ebom_leaf_codes - mbom_ebom_refs:
                item = ebom_map.get(code)
                diffs.append(DiffItem(
                    item_code=code,
                    item_name=item.name if item else "",
                    diff_type=DiffType.UNMAPPED,
                    source_bom="ebom",
                    target_bom="mbom",
                    details={"reason": "eBOM item not mapped to mBOM"},
                    suggestion=SyncSuggestion.MANUAL_CONFIRM,
                ))

            for item in mbom_items:
                if item.mapping_status == "unmapped":
                    diffs.append(DiffItem(
                        item_code=item.item_code,
                        item_name=item.name,
                        diff_type=DiffType.UNMAPPED,
                        source_bom="mbom",
                        target_bom="ebom",
                        details={"reason": "mBOM item has no eBOM mapping"},
                        suggestion=SyncSuggestion.MANUAL_CONFIRM,
                    ))

        if sbom and sbom.root_item:
            sbom_items = sbom.root_item.flatten()
            sbom_codes = {i.item_code for i in sbom_items}

            if mbom and mbom.root_item:
                mbom_items = mbom.root_item.flatten()
                mbom_codes = {i.item_code for i in mbom_items}

                for code in sbom_codes - mbom_codes:
                    item = next((i for i in sbom_items if i.item_code == code), None)
                    diffs.append(DiffItem(
                        item_code=code,
                        item_name=item.name if item else "",
                        diff_type=DiffType.ADDED,
                        source_bom="sbom",
                        target_bom="mbom",
                        details={"reason": "sBOM item not in mBOM"},
                        suggestion=SyncSuggestion.MANUAL_CONFIRM,
                    ))

                for code in mbom_codes - sbom_codes:
                    item = next((i for i in mbom_items if i.item_code == code), None)
                    diffs.append(DiffItem(
                        item_code=code,
                        item_name=item.name if item else "",
                        diff_type=DiffType.REMOVED,
                        source_bom="mbom",
                        target_bom="sbom",
                        details={"reason": "mBOM item not in sBOM"},
                        suggestion=SyncSuggestion.AUTO_SYNC,
                    ))

        return diffs

    def suggest_sync(self, diffs: list[DiffItem]) -> dict[str, Any]:
        auto_sync = [d for d in diffs if d.suggestion == SyncSuggestion.AUTO_SYNC]
        manual_confirm = [d for d in diffs if d.suggestion == SyncSuggestion.MANUAL_CONFIRM]

        return {
            "total_diffs": len(diffs),
            "auto_sync_count": len(auto_sync),
            "manual_confirm_count": len(manual_confirm),
            "auto_sync_items": [d.to_dict() for d in auto_sync],
            "manual_confirm_items": [d.to_dict() for d in manual_confirm],
            "recommendation": (
                f"{len(auto_sync)} items can be auto-synced, "
                f"{len(manual_confirm)} items require manual confirmation"
            ),
        }

    def _check_attribute_consistency(
        self,
        ebom: EBOM,
        mbom: MBOM | None,
        sbom: SBOM | None,
        report: ConsistencyReport,
    ) -> None:
        if ebom.root_item is None:
            return

        ebom_items = ebom.root_item.flatten()
        inconsistencies: list[dict[str, Any]] = []

        if mbom and mbom.root_item:
            mbom_items = mbom.root_item.flatten()
            mbom_map = {i.ebom_item_code: i for i in mbom_items if i.ebom_item_code}

            for ebom_item in ebom_items:
                mbom_item = mbom_map.get(ebom_item.item_code)
                if mbom_item:
                    if ebom_item.name != mbom_item.name:
                        inconsistencies.append({
                            "item_code": ebom_item.item_code,
                            "attribute": "name",
                            "ebom_value": ebom_item.name,
                            "mbom_value": mbom_item.name,
                        })
                    if ebom_item.quantity != mbom_item.quantity:
                        inconsistencies.append({
                            "item_code": ebom_item.item_code,
                            "attribute": "quantity",
                            "ebom_value": ebom_item.quantity,
                            "mbom_value": mbom_item.quantity,
                        })

        report.attribute_consistency = {
            "total_checked": len(ebom_items),
            "inconsistencies": inconsistencies,
            "inconsistency_count": len(inconsistencies),
        }

        if inconsistencies:
            report.is_consistent = False
            report.warnings.append(f"{len(inconsistencies)} attribute inconsistencies detected")