from __future__ import annotations

import logging
from enum import Enum
from typing import Any

from aeroforge_common.utils.helpers import generate_code

from ..entities.bom_item import BOMItem, EBOM, MBOM, SBOM

logger = logging.getLogger(__name__)


class MaintenanceStrategy(str, Enum):
    SCHEDULED_REPLACEMENT = "scheduled_replacement"
    CONDITION_BASED = "condition_based"
    FAILURE_BASED = "failure_based"


class SparePartCategory(str, Enum):
    ESSENTIAL = "essential"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"


MAINTENANCE_STRATEGY_TEMPLATES: dict[str, dict[str, Any]] = {
    "structural": {
        "strategy": MaintenanceStrategy.SCHEDULED_REPLACEMENT,
        "default_replacement_cycle_fh": 60000,
        "inspection_interval_fh": 3000,
        "spare_category": SparePartCategory.ESSENTIAL,
        "procurement_lead_time_days": 90,
        "accessibility": "requires_disassembly",
    },
    "skin": {
        "strategy": MaintenanceStrategy.CONDITION_BASED,
        "default_replacement_cycle_fh": 80000,
        "inspection_interval_fh": 2000,
        "spare_category": SparePartCategory.RECOMMENDED,
        "procurement_lead_time_days": 120,
        "accessibility": "visual_inspection",
    },
    "virtual_assembly": {
        "strategy": MaintenanceStrategy.CONDITION_BASED,
        "default_replacement_cycle_fh": 0,
        "inspection_interval_fh": 1000,
        "spare_category": SparePartCategory.OPTIONAL,
        "procurement_lead_time_days": 0,
        "accessibility": "n_a",
    },
    "default": {
        "strategy": MaintenanceStrategy.CONDITION_BASED,
        "default_replacement_cycle_fh": 50000,
        "inspection_interval_fh": 3000,
        "spare_category": SparePartCategory.RECOMMENDED,
        "procurement_lead_time_days": 60,
        "accessibility": "standard_access",
    },
}

MATERIAL_FATIGUE_FACTORS: dict[str, float] = {
    "CFRP": 1.2,
    "aluminum": 1.0,
    "steel": 0.8,
    "titanium": 1.1,
    "composite": 1.15,
}

ENVIRONMENT_ADJUSTMENTS: dict[str, float] = {
    "standard": 1.0,
    "corrosive": 0.8,
    "high_temperature": 0.85,
    "high_humidity": 0.9,
    "arid": 1.05,
}


class SBOMGenerator:
    def generate_from_ebom(
        self,
        ebom: EBOM,
        mbom: MBOM | None = None,
        environment: str = "standard",
        created_by: str = "",
    ) -> SBOM:
        if ebom.root_item is None:
            raise ValueError("Cannot generate sBOM from empty eBOM")

        sbom = SBOM(ebom_id=ebom.id, mbom_id=mbom.id if mbom else "", created_by=created_by)

        source_root = mbom.root_item if mbom and mbom.root_item else ebom.root_item

        sbom_root = self._transform_to_sbom_item(source_root, environment)
        sbom.set_root(sbom_root)

        self.apply_maintenance_strategy(sbom, environment)
        self.mark_spare_parts(sbom)
        self.assign_replacement_cycle(sbom, environment)

        logger.info(
            "sBOM generated: ebom_id=%s sbom_id=%s",
            ebom.id, sbom.id,
        )
        return sbom

    def _transform_to_sbom_item(self, source: BOMItem, environment: str) -> BOMItem:
        sbom_item = BOMItem(
            item_code=source.item_code,
            name=source.name,
            bom_type="sbom",
            quantity=source.quantity,
            unit=source.unit,
            version=source.version,
            part_type=source.part_type,
            attributes=dict(source.attributes),
            station=source.station,
            assembly_order=source.assembly_order,
            is_virtual=source.is_virtual,
            ebom_item_code=source.ebom_item_code or source.item_code,
        )

        for child in source.children:
            sbom_child = self._transform_to_sbom_item(child, environment)
            sbom_item.add_child(sbom_child)

        return sbom_item

    def apply_maintenance_strategy(self, sbom: SBOM, environment: str = "standard") -> None:
        if sbom.root_item is None:
            return

        all_items = sbom.root_item.flatten()
        for item in all_items:
            template = self._get_template_for_item(item)
            item.attributes["maintenance_strategy"] = template["strategy"].value
            item.attributes["inspection_interval_fh"] = template["inspection_interval_fh"]
            item.attributes["accessibility"] = template["accessibility"]

            env_factor = ENVIRONMENT_ADJUSTMENTS.get(environment, 1.0)
            adjusted_interval = int(template["inspection_interval_fh"] * env_factor)
            item.attributes["adjusted_inspection_interval_fh"] = adjusted_interval

            parent_path = self._get_parent_path(item, sbom.root_item)
            if parent_path:
                item.attributes["maintenance_access_path"] = parent_path

    def mark_spare_parts(self, sbom: SBOM) -> None:
        if sbom.root_item is None:
            return

        all_items = sbom.root_item.flatten()
        for item in all_items:
            if item.is_virtual:
                continue

            template = self._get_template_for_item(item)
            category = template["spare_category"]

            item.attributes["spare_part_category"] = category.value
            item.attributes["recommended_spare_quantity"] = max(1, item.quantity)
            item.attributes["procurement_lead_time_days"] = template["procurement_lead_time_days"]

            if category == SparePartCategory.ESSENTIAL:
                item.attributes["safety_critical"] = True

    def assign_replacement_cycle(self, sbom: SBOM, environment: str = "standard") -> None:
        if sbom.root_item is None:
            return

        all_items = sbom.root_item.flatten()
        env_factor = ENVIRONMENT_ADJUSTMENTS.get(environment, 1.0)

        for item in all_items:
            if item.is_virtual:
                item.attributes["replacement_cycle_fh"] = 0
                continue

            template = self._get_template_for_item(item)
            base_cycle = template["default_replacement_cycle_fh"]

            material = item.attributes.get("material", "aluminum")
            if isinstance(material, str):
                mat_factor = MATERIAL_FATIGUE_FACTORS.get(material.lower(), 1.0)
            else:
                mat_factor = 1.0

            adjusted_cycle = int(base_cycle * mat_factor * env_factor)
            item.attributes["replacement_cycle_fh"] = adjusted_cycle
            item.attributes["material_fatigue_factor"] = mat_factor
            item.attributes["environment_factor"] = env_factor

    def _get_template_for_item(self, item: BOMItem) -> dict[str, Any]:
        part_type = item.part_type.lower()
        if part_type in MAINTENANCE_STRATEGY_TEMPLATES:
            return MAINTENANCE_STRATEGY_TEMPLATES[part_type]
        return MAINTENANCE_STRATEGY_TEMPLATES["default"]

    def _get_parent_path(self, target: BOMItem, root: BOMItem, path: list[str] | None = None) -> str | None:
        if path is None:
            path = []
        if target.item_code == root.item_code:
            return " → ".join(path) if path else None
        for child in root.children:
            result = self._get_parent_path(target, child, path + [root.name])
            if result is not None:
                return result
        return None