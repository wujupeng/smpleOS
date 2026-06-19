from __future__ import annotations

import logging
from typing import Optional

from ..entities.config_item import ConfigItem
from ..entities.config_baseline import ConfigBaseline
from ..entities.config_change import ConfigChange
from ..value_objects.config_item_type import ConfigItemType
from ..value_objects.propagation_action import PropagationAction

logger = logging.getLogger(__name__)


class ConfigItemService:
    def __init__(self) -> None:
        self._items: dict[str, ConfigItem] = {}

    def create_item(
        self,
        item_number: str,
        item_name: str,
        item_type: str,
        description: str = "",
        owner_id: str | None = None,
        properties: dict | None = None,
    ) -> ConfigItem:
        ConfigItemType(item_type)
        item = ConfigItem(
            item_number=item_number,
            item_name=item_name,
            item_type=item_type,
            description=description,
            owner_id=owner_id,
            properties=properties or {},
        )
        self._items[item.item_id] = item
        logger.info(f"Config item created: {item_number} ({item_type})")
        return item

    def get_item(self, item_id: str) -> Optional[ConfigItem]:
        return self._items.get(item_id)

    def update_item(self, item_id: str, **kwargs) -> ConfigItem:
        item = self._get_or_raise(item_id)
        for key, value in kwargs.items():
            if hasattr(item, key) and key not in ("item_id",):
                setattr(item, key, value)
        item.updated_at = item.updated_at
        return item

    def transition_lifecycle(self, item_id: str, new_lifecycle: str) -> ConfigItem:
        item = self._get_or_raise(item_id)
        item.transition_lifecycle(new_lifecycle)
        return item

    def search_items(
        self,
        item_type: str | None = None,
        status: str | None = None,
        owner_id: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[ConfigItem]:
        items = list(self._items.values())
        if item_type:
            items = [i for i in items if i.item_type == item_type]
        if status:
            items = [i for i in items if i.status == status]
        if owner_id:
            items = [i for i in items if i.owner_id == owner_id]
        return items[skip : skip + limit]

    def _get_or_raise(self, item_id: str) -> ConfigItem:
        item = self._items.get(item_id)
        if not item:
            raise ValueError(f"Config item {item_id} not found")
        return item


class ConfigBaselineService:
    def __init__(self) -> None:
        self._baselines: dict[str, ConfigBaseline] = {}

    def create_baseline(
        self,
        baseline_name: str,
        baseline_type: str = "product",
        description: str = "",
        aircraft_config: str | None = None,
        created_by: str | None = None,
    ) -> ConfigBaseline:
        baseline = ConfigBaseline(
            baseline_name=baseline_name,
            baseline_type=baseline_type,
            description=description,
            aircraft_config=aircraft_config,
            created_by=created_by,
        )
        self._baselines[baseline.baseline_id] = baseline
        logger.info(f"Baseline created: {baseline_name}")
        return baseline

    def get_baseline(self, baseline_id: str) -> Optional[ConfigBaseline]:
        return self._baselines.get(baseline_id)

    def freeze_baseline(self, baseline_id: str, frozen_by: str) -> ConfigBaseline:
        baseline = self._get_or_raise(baseline_id)
        baseline.freeze(frozen_by)
        return baseline

    def unfreeze_baseline(self, baseline_id: str) -> ConfigBaseline:
        baseline = self._get_or_raise(baseline_id)
        baseline.unfreeze()
        return baseline

    def add_item_to_baseline(
        self, baseline_id: str, item: ConfigItem, version: int | None = None
    ) -> ConfigBaseline:
        baseline = self._get_or_raise(baseline_id)
        baseline.add_item(item, version)
        return baseline

    def get_baseline_items(self, baseline_id: str) -> dict[str, int]:
        baseline = self._get_or_raise(baseline_id)
        return baseline.get_items()

    def compare_baselines(self, baseline_a_id: str, baseline_b_id: str) -> dict:
        ba = self._get_or_raise(baseline_a_id)
        bb = self._get_or_raise(baseline_b_id)
        items_a = ba.get_items()
        items_b = bb.get_items()
        added = {k: v for k, v in items_b.items() if k not in items_a}
        removed = {k: v for k, v in items_a.items() if k not in items_b}
        common = set(items_a.keys()) & set(items_b.keys())
        modified = {k: {"from": items_a[k], "to": items_b[k]} for k in common if items_a[k] != items_b[k]}
        return {
            "baseline_a": ba.baseline_name,
            "baseline_b": bb.baseline_name,
            "items_added": len(added),
            "items_removed": len(removed),
            "items_modified": len(modified),
            "added": added,
            "removed": removed,
            "modified": modified,
        }

    def _get_or_raise(self, baseline_id: str) -> ConfigBaseline:
        baseline = self._baselines.get(baseline_id)
        if not baseline:
            raise ValueError(f"Baseline {baseline_id} not found")
        return baseline


class ConfigChangeService:
    def __init__(self, item_service: ConfigItemService) -> None:
        self._changes: dict[str, ConfigChange] = {}
        self._item_service = item_service

    def create_change(
        self,
        change_type: str,
        title: str,
        description: str,
        affected_items: list[dict] | None = None,
        priority: str = "medium",
        requested_by: str | None = None,
    ) -> ConfigChange:
        change = ConfigChange(
            change_type=change_type,
            title=title,
            description=description,
            affected_items=affected_items or [],
            priority=priority,
            requested_by=requested_by,
        )
        self._changes[change.change_id] = change
        logger.info(f"Change created: {title} ({change_type})")
        return change

    def get_change(self, change_id: str) -> Optional[ConfigChange]:
        return self._changes.get(change_id)

    def propagate_change(self, change_id: str, impact_data: dict | None = None) -> ConfigChange:
        change = self._get_or_raise(change_id)
        for item_info in change.affected_items:
            item_id = item_info.get("item_id")
            if not item_id:
                continue
            item = self._item_service.get_item(item_id)
            if not item:
                continue
            if item.item_type in ("wing", "tail", "fuselage"):
                change.add_propagation(item_id, item_id, PropagationAction.UPDATE_VERSION.value)
            if item.item_type in ("motor", "battery", "esc"):
                change.add_propagation(item_id, item_id, PropagationAction.RETEST.value)
            change.add_propagation(item_id, item_id, PropagationAction.NOTIFY.value)
        change.propagation_map = {"propagated_count": len(change.get_propagations())}
        return change

    def approve_change(self, change_id: str, approver_id: str) -> ConfigChange:
        change = self._get_or_raise(change_id)
        change.approve(approver_id)
        return change

    def implement_change(self, change_id: str) -> ConfigChange:
        change = self._get_or_raise(change_id)
        change.implement()
        for item_info in change.affected_items:
            item_id = item_info.get("item_id")
            if item_id:
                item = self._item_service.get_item(item_id)
                if item and item.status != "baselined":
                    item.update_properties(item_info.get("new_properties", {}))
        change.complete()
        return change

    def analyze_impact(self, change_id: str) -> dict:
        change = self._get_or_raise(change_id)
        affected = []
        for item_info in change.affected_items:
            item_id = item_info.get("item_id")
            item = self._item_service.get_item(item_id) if item_id else None
            if item:
                affected.append({
                    "item_id": item.item_id,
                    "item_type": item.item_type,
                    "current_version": item.current_version,
                    "status": item.status,
                    "lifecycle": item.lifecycle,
                })
        return {
            "change_id": change.change_id,
            "impact_level": change.impact_level,
            "affected_items": affected,
            "propagation_count": len(change.get_propagations()),
        }

    def _get_or_raise(self, change_id: str) -> ConfigChange:
        change = self._changes.get(change_id)
        if not change:
            raise ValueError(f"Change {change_id} not found")
        return change


class ConfigCompatibilityService:
    def validate_compatibility(
        self, items: list[ConfigItem], rules: list[dict] | None = None
    ) -> dict:
        default_rules = [
            {"source_type": "motor", "target_type": "esc", "rule_type": "requires", "severity": "error"},
            {"source_type": "motor", "target_type": "battery", "rule_type": "requires", "severity": "error"},
            {"source_type": "battery", "target_type": "esc", "rule_type": "requires", "severity": "error"},
        ]
        rules = rules or default_rules
        violations = []
        for rule in rules:
            source_items = [i for i in items if i.item_type == rule["source_type"]]
            target_items = [i for i in items if i.item_type == rule["target_type"]]
            if rule["rule_type"] == "requires" and source_items and not target_items:
                violations.append({
                    "rule": rule,
                    "message": f"{rule['source_type']} requires {rule['target_type']} but none found",
                    "severity": rule["severity"],
                })
        return {
            "is_compatible": len(violations) == 0,
            "violations": violations,
            "total_rules_checked": len(rules),
        }