import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'services', 'configuration-center'))

from src.domain.entities.config_item import ConfigItem
from src.domain.entities.config_baseline import ConfigBaseline
from src.domain.entities.config_change import ConfigChange
from src.domain.services.config_services import (
    ConfigItemService,
    ConfigBaselineService,
    ConfigChangeService,
    ConfigCompatibilityService,
)


class TestConfigItemCRUDIntegration:
    def test_item_crud_lifecycle(self):
        svc = ConfigItemService()
        item = svc.create_item(item_number="AF-X01-WING", item_name="Main Wing", item_type="wing")
        assert svc.get_item(item.item_id) is not None
        item.release()
        assert item.status == "released"
        item.baseline()
        assert item.status == "baselined"


class TestBaselineFreezeIntegration:
    def test_baseline_create_freeze_unfreeze(self):
        item_svc = ConfigItemService()
        bl_svc = ConfigBaselineService()
        item = item_svc.create_item(item_number="AF-X01-WING", item_name="Wing", item_type="wing")
        baseline = bl_svc.create_baseline(baseline_name="Product Baseline v1.0")
        bl_svc.add_item_to_baseline(baseline.baseline_id, item)
        frozen = bl_svc.freeze_baseline(baseline.baseline_id, "admin")
        assert frozen.status == "frozen"
        unfrozen = bl_svc.unfreeze_baseline(baseline.baseline_id)
        assert unfrozen.status == "open"


class TestBaselineComparisonIntegration:
    def test_baseline_comparison(self):
        item_svc = ConfigItemService()
        bl_svc = ConfigBaselineService()
        item1 = item_svc.create_item(item_number="AF-X01-WING", item_name="Wing", item_type="wing")
        item2 = item_svc.create_item(item_number="AF-X01-MOTOR", item_name="Motor", item_type="motor")
        bl_a = bl_svc.create_baseline(baseline_name="v1")
        bl_svc.add_item_to_baseline(bl_a.baseline_id, item1)
        bl_b = bl_svc.create_baseline(baseline_name="v2")
        bl_svc.add_item_to_baseline(bl_b.baseline_id, item1)
        bl_svc.add_item_to_baseline(bl_b.baseline_id, item2)
        diff = bl_svc.compare_baselines(bl_a.baseline_id, bl_b.baseline_id)
        assert diff["items_added"] == 1
        assert diff["items_removed"] == 0


class TestChangePropagationIntegration:
    def test_change_create_propagate_approve_implement(self):
        item_svc = ConfigItemService()
        change_svc = ConfigChangeService(item_svc)
        item = item_svc.create_item(item_number="AF-X01-WING", item_name="Wing", item_type="wing")
        change = change_svc.create_change(
            change_type="engineering_change",
            title="Wing span increase",
            description="Increase wing span to 2.6m",
            affected_items=[{"item_id": item.item_id}],
        )
        change.submit()
        propagated = change_svc.propagate_change(change.change_id)
        assert len(propagated.get_propagations()) > 0
        change_svc.approve_change(change.change_id, "approver1")
        assert change.status == "approved"
        implemented = change_svc.implement_change(change.change_id)
        assert implemented.status == "completed"


class TestCompatibilityValidationIntegration:
    def test_full_compatibility_check(self):
        item_svc = ConfigItemService()
        compat_svc = ConfigCompatibilityService()
        motor = item_svc.create_item(item_number="M1", item_name="Motor", item_type="motor")
        esc = item_svc.create_item(item_number="E1", item_name="ESC", item_type="esc")
        battery = item_svc.create_item(item_number="B1", item_name="Battery", item_type="battery")
        result = compat_svc.validate_compatibility([motor, esc, battery])
        assert result["is_compatible"] is True

    def test_incompatible_configuration(self):
        compat_svc = ConfigCompatibilityService()
        motor = ConfigItem(item_type="motor", item_number="M1", item_name="Motor")
        result = compat_svc.validate_compatibility([motor])
        assert result["is_compatible"] is False
        assert any(v["rule"]["source_type"] == "motor" for v in result["violations"])


class TestConfigChangeBaselineLinkIntegration:
    def test_change_affects_baselined_item(self):
        item_svc = ConfigItemService()
        bl_svc = ConfigBaselineService()
        change_svc = ConfigChangeService(item_svc)
        item = item_svc.create_item(item_number="AF-X01-WING", item_name="Wing", item_type="wing")
        item.release()
        item.baseline()
        baseline = bl_svc.create_baseline(baseline_name="v1")
        bl_svc.add_item_to_baseline(baseline.baseline_id, item)
        bl_svc.freeze_baseline(baseline.baseline_id, "admin")
        change = change_svc.create_change(
            change_type="engineering_change",
            title="Wing modification",
            description="Modify wing parameters",
            affected_items=[{"item_id": item.item_id}],
            priority="high",
        )
        change.submit()
        impact = change_svc.analyze_impact(change.change_id)
        assert len(impact["affected_items"]) == 1
        assert impact["affected_items"][0]["status"] == "baselined"