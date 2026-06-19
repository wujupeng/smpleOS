from __future__ import annotations

import logging
from typing import Optional

from ..entities.bom_entities import EBOM, MBOM, SBOM, BOMLine

logger = logging.getLogger(__name__)


class EBOMService:
    def __init__(self) -> None:
        self._eboms: dict[str, EBOM] = {}

    def generate_ebom(self, bom_number: str, product_id: str, lines_data: list[dict] | None = None, created_by: str | None = None) -> EBOM:
        ebom = EBOM(bom_number=bom_number, product_id=product_id, created_by=created_by)
        for ld in (lines_data or []):
            ebom.add_line(BOMLine(
                part_number=ld.get("part_number", ""),
                part_name=ld.get("part_name", ""),
                quantity=ld.get("quantity", 1),
                unit=ld.get("unit", "ea"),
                material_ref=ld.get("material_ref"),
            ))
        self._eboms[ebom.bom_id] = ebom
        logger.info(f"eBOM generated: {bom_number}")
        return ebom

    def get_ebom(self, bom_id: str) -> Optional[EBOM]:
        return self._eboms.get(bom_id)

    def update_ebom(self, bom_id: str, **kwargs) -> EBOM:
        ebom = self._get_or_raise(bom_id)
        for k, v in kwargs.items():
            if hasattr(ebom, k) and k not in ("bom_id",):
                setattr(ebom, k, v)
        ebom.updated_at = ebom.updated_at
        return ebom

    def get_ebom_tree(self, bom_id: str) -> list[dict]:
        ebom = self._get_or_raise(bom_id)
        return ebom.get_tree()

    def _get_or_raise(self, bom_id: str) -> EBOM:
        ebom = self._eboms.get(bom_id)
        if not ebom:
            raise ValueError(f"eBOM {bom_id} not found")
        return ebom


class BOMTransformService:
    def __init__(self, ebom_service: EBOMService) -> None:
        self._ebom_service = ebom_service
        self._mboms: dict[str, MBOM] = {}
        self._sboms: dict[str, SBOM] = {}

    def transform_to_mbom(self, ebom_id: str, bom_number: str, created_by: str | None = None) -> MBOM:
        ebom = self._ebom_service.get_ebom(ebom_id)
        if not ebom:
            raise ValueError(f"eBOM {ebom_id} not found")
        if ebom.status != "released":
            raise ValueError("eBOM must be released before transformation")
        mbom = MBOM(bom_number=bom_number, product_id=ebom.product_id, ebom_ref=ebom.bom_id, created_by=created_by)
        for line in ebom.lines:
            mbom.add_line(BOMLine(
                part_number=line.part_number,
                part_name=line.part_name,
                quantity=line.quantity,
                unit=line.unit,
                sort_order=line.sort_order,
            ))
        self._mboms[mbom.bom_id] = mbom
        logger.info(f"mBOM created from eBOM {ebom_id}: {bom_number}")
        return mbom

    def transform_to_sbom(self, ebom_id: str, bom_number: str, created_by: str | None = None) -> SBOM:
        ebom = self._ebom_service.get_ebom(ebom_id)
        if not ebom:
            raise ValueError(f"eBOM {ebom_id} not found")
        sbom = SBOM(bom_number=bom_number, product_id=ebom.product_id, ebom_ref=ebom.bom_id, created_by=created_by)
        for line in ebom.lines:
            sbom.add_line(BOMLine(
                part_number=line.part_number,
                part_name=line.part_name,
                quantity=line.quantity,
                unit=line.unit,
            ))
        self._sboms[sbom.bom_id] = sbom
        logger.info(f"sBOM created from eBOM {ebom_id}: {bom_number}")
        return sbom

    def get_mbom(self, bom_id: str) -> Optional[MBOM]:
        return self._mboms.get(bom_id)

    def get_sbom(self, bom_id: str) -> Optional[SBOM]:
        return self._sboms.get(bom_id)


class BOMSyncService:
    def __init__(self, ebom_service: EBOMService, transform_service: BOMTransformService) -> None:
        self._ebom_service = ebom_service
        self._transform_service = transform_service

    def detect_differences(self, ebom_id: str, target_bom_type: str, target_bom_id: str) -> list[dict]:
        ebom = self._ebom_service.get_ebom(ebom_id)
        if not ebom:
            raise ValueError(f"eBOM {ebom_id} not found")
        target = None
        if target_bom_type == "mbom":
            target = self._transform_service.get_mbom(target_bom_id)
        elif target_bom_type == "sbom":
            target = self._transform_service.get_sbom(target_bom_id)
        if not target:
            return []
        ebom_parts = {l.part_number: l for l in ebom.lines}
        target_parts = {l.part_number: l for l in target.lines}
        diffs = []
        for pn in set(ebom_parts.keys()) | set(target_parts.keys()):
            if pn in ebom_parts and pn not in target_parts:
                diffs.append({"part_number": pn, "type": "added_in_ebom", "action": "add_to_target"})
            elif pn not in ebom_parts and pn in target_parts:
                diffs.append({"part_number": pn, "type": "removed_from_ebom", "action": "remove_from_target"})
            elif pn in ebom_parts and pn in target_parts:
                if ebom_parts[pn].quantity != target_parts[pn].quantity:
                    diffs.append({"part_number": pn, "type": "quantity_changed", "ebom_qty": ebom_parts[pn].quantity, "target_qty": target_parts[pn].quantity})
        return diffs

    def sync_bom(self, ebom_id: str, target_bom_type: str, target_bom_id: str) -> dict:
        diffs = self.detect_differences(ebom_id, target_bom_type, target_bom_id)
        synced = len(diffs)
        return {
            "ebom_id": ebom_id,
            "target_bom_id": target_bom_id,
            "target_type": target_bom_type,
            "differences_found": len(diffs),
            "synced_count": synced,
            "status": "synced" if synced >= 0 else "failed",
        }