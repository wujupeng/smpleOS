import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'services', 'configuration-center'))

from src.domain.entities.config_item import ConfigItem
from src.domain.entities.config_baseline import ConfigBaseline
from src.domain.entities.config_change import ConfigChange
from src.domain.value_objects.config_item_type import ConfigItemType
from src.domain.value_objects.config_item_status import ConfigItemStatus
from src.domain.value_objects.propagation_action import PropagationAction
from src.domain.services.config_services import (
    ConfigItemService,
    ConfigBaselineService,
    ConfigChangeService,
    ConfigCompatibilityService,
)


class TestConfigItem:
    def test_create_item(self):
        item = ConfigItem(item_number="AF-X01-WING", item_name="Main Wing", item_type="wing")
        assert item.item_number == "AF-X01-WING"
        assert item.status == ConfigItemStatus.DRAFT

    def test_release_item(self):
        item = ConfigItem(item_number="AF-X01-WING", item_name="Main Wing", item_type="wing")
        item.release()
        assert item.status == ConfigItemStatus.RELEASED

    def test_release_non_draft_raises(self):
        item = ConfigItem(item_number="AF-X01-WING", item_name="Main Wing", item_type="wing", status=ConfigItemStatus.RELEASED)
        with pytest.raises(ValueError):
            item.release()

    def test_baseline_item(self):
        item = ConfigItem(item_number="AF-X01-WING", item_name="Main Wing", item_type="wing", status=ConfigItemStatus.RELEASED)
        item.baseline()
        assert item.status == ConfigItemStatus.BASELINED

    def test_baseline_non_released_raises(self):
        item = ConfigItem(item_number="AF-X01-WING", item_name="Main Wing", item_type="wing")
        with pytest.raises(ValueError):
            item.baseline()

    def test_obsolete_item(self):
        item = ConfigItem(item_number="AF-X01-WING", item_name="Main Wing", item_type="wing", status=ConfigItemStatus.BASELINED)
        item.obsolete()
        assert item.status == ConfigItemStatus.OBSOLETE

    def test_transition_lifecycle(self):
        item = ConfigItem(item_number="AF-X01-WING", item_name="Main Wing", item_type="wing", lifecycle="development")
        item.transition_lifecycle("production")
        assert item.lifecycle == "production"

    def test_invalid_lifecycle_transition_raises(self):
        item = ConfigItem(item_number="AF-X01-WING", item_name="Main Wing", item_type="wing", lifecycle="development")
        with pytest.raises(ValueError):
            item.transition_lifecycle("retired")

    def test_update_properties(self):
        item = ConfigItem(item_number="AF-X01-WING", item_name="Main Wing", item_type="wing")
        item.update_properties({"span": 2400})
        assert item.properties["span"] == 2400
        assert item.current_version == 2

    def test_update_baselined_item_raises(self):
        item = ConfigItem(item_number="AF-X01-WING", item_name="Main Wing", item_type="wing", status=ConfigItemStatus.BASELINED)
        with pytest.raises(ValueError, match="Cannot modify baselined"):
            item.update_properties({"span": 2400})

    def test_to_dict(self):
        item = ConfigItem(item_number="AF-X01-WING", item_name="Main Wing", item_type="wing")
        d = item.to_dict()
        assert d["item_number"] == "AF-X01-WING"
        assert d["status"] == ConfigItemStatus.DRAFT


class TestConfigBaseline:
    def test_create_baseline(self):
        baseline = ConfigBaseline(baseline_name="Product Baseline v1.0")
        assert baseline.status == "open"

    def test_add_item(self):
        baseline = ConfigBaseline(baseline_name="Test")
        item = ConfigItem(item_number="AF-X01-WING", item_name="Wing", item_type="wing", current_version=2)
        baseline.add_item(item)
        items = baseline.get_items()
        assert item.item_id in items
        assert items[item.item_id] == 2

    def test_add_item_to_frozen_raises(self):
        baseline = ConfigBaseline(baseline_name="Test", status="frozen")
        item = ConfigItem(item_number="AF-X01-WING", item_name="Wing", item_type="wing")
        with pytest.raises(ValueError, match="frozen"):
            baseline.add_item(item)

    def test_freeze_baseline(self):
        baseline = ConfigBaseline(baseline_name="Test")
        item = ConfigItem(item_number="AF-X01-WING", item_name="Wing", item_type="wing")
        baseline.add_item(item)
        baseline.freeze("admin")
        assert baseline.status == "frozen"
        assert baseline.frozen_by == "admin"

    def test_freeze_empty_baseline_raises(self):
        baseline = ConfigBaseline(baseline_name="Test")
        with pytest.raises(ValueError, match="empty"):
            baseline.freeze("admin")

    def test_unfreeze_baseline(self):
        baseline = ConfigBaseline(baseline_name="Test")
        item = ConfigItem(item_number="AF-X01-WING", item_name="Wing", item_type="wing")
        baseline.add_item(item)
        baseline.freeze("admin")
        baseline.unfreeze()
        assert baseline.status == "open"
        assert baseline.frozen_at is None

    def test_remove_item(self):
        baseline = ConfigBaseline(baseline_name="Test")
        item = ConfigItem(item_number="AF-X01-WING", item_name="Wing", item_type="wing")
        baseline.add_item(item)
        baseline.remove_item(item.item_id)
        assert item.item_id not in baseline.get_items()


class TestConfigChange:
    def test_create_change(self):
        change = ConfigChange(change_type="engineering_change", title="Wing span increase", description="Increase wing span to 2.6m")
        assert change.status == "proposed"

    def test_submit_change(self):
        change = ConfigChange(change_type="engineering_change", title="Test", description="Test")
        change.submit()
        assert change.status == "under_review"

    def test_approve_change(self):
        change = ConfigChange(change_type="engineering_change", title="Test", description="Test", status="under_review")
        change.approve("approver1")
        assert change.status == "approved"
        assert change.approver_id == "approver1"

    def test_reject_change(self):
        change = ConfigChange(change_type="engineering_change", title="Test", description="Test", status="under_review")
        change.reject()
        assert change.status == "rejected"

    def test_implement_change(self):
        change = ConfigChange(change_type="engineering_change", title="Test", description="Test", status="approved")
        change.implement()
        assert change.status == "implementing"

    def test_complete_change(self):
        change = ConfigChange(change_type="engineering_change", title="Test", description="Test", status="implementing")
        change.complete()
        assert change.status == "completed"
        assert change.implemented_at is not None

    def test_add_propagation(self):
        change = ConfigChange(change_type="engineering_change", title="Test", description="Test")
        change.add_propagation("item1", "item2", "update_version")
        props = change.get_propagations()
        assert len(props) == 1
        assert props[0]["action"] == "update_version"


class TestConfigItemService:
    def test_create_item(self):
        svc = ConfigItemService()
        item = svc.create_item(item_number="AF-X01-WING", item_name="Wing", item_type="wing")
        assert item.item_number == "AF-X01-WING"

    def test_create_item_invalid_type_raises(self):
        svc = ConfigItemService()
        with pytest.raises(ValueError):
            svc.create_item(item_number="X", item_name="X", item_type="invalid")

    def test_search_items(self):
        svc = ConfigItemService()
        svc.create_item(item_number="AF-X01-WING", item_name="Wing", item_type="wing")
        svc.create_item(item_number="AF-X01-MOTOR", item_name="Motor", item_type="motor")
        results = svc.search_items(item_type="wing")
        assert len(results) == 1

    def test_transition_lifecycle(self):
        svc = ConfigItemService()
        item = svc.create_item(item_number="AF-X01-WING", item_name="Wing", item_type="wing")
        updated = svc.transition_lifecycle(item.item_id, "production")
        assert updated.lifecycle == "production"


class TestConfigBaselineService:
    def test_create_baseline(self):
        svc = ConfigBaselineService()
        baseline = svc.create_baseline(baseline_name="Product Baseline v1.0")
        assert baseline.baseline_name == "Product Baseline v1.0"

    def test_freeze_baseline(self):
        item_svc = ConfigItemService()
        bl_svc = ConfigBaselineService()
        item = item_svc.create_item(item_number="AF-X01-WING", item_name="Wing", item_type="wing")
        baseline = bl_svc.create_baseline(baseline_name="Test")
        bl_svc.add_item_to_baseline(baseline.baseline_id, item)
        frozen = bl_svc.freeze_baseline(baseline.baseline_id, "admin")
        assert frozen.status == "frozen"

    def test_compare_baselines(self):
        item_svc = ConfigItemService()
        bl_svc = ConfigBaselineService()
        item = item_svc.create_item(item_number="AF-X01-WING", item_name="Wing", item_type="wing")
        bl_a = bl_svc.create_baseline(baseline_name="v1")
        bl_svc.add_item_to_baseline(bl_a.baseline_id, item)
        bl_b = bl_svc.create_baseline(baseline_name="v2")
        diff = bl_svc.compare_baselines(bl_a.baseline_id, bl_b.baseline_id)
        assert diff["items_removed"] == 1


class TestConfigChangeService:
    def test_create_change(self):
        item_svc = ConfigItemService()
        change_svc = ConfigChangeService(item_svc)
        change = change_svc.create_change(change_type="engineering_change", title="Test", description="Test")
        assert change.status == "proposed"

    def test_approve_change(self):
        item_svc = ConfigItemService()
        change_svc = ConfigChangeService(item_svc)
        change = change_svc.create_change(change_type="engineering_change", title="Test", description="Test")
        change.submit()
        change_svc.approve_change(change.change_id, "approver1")
        assert change.status == "approved"

    def test_analyze_impact(self):
        item_svc = ConfigItemService()
        change_svc = ConfigChangeService(item_svc)
        item = item_svc.create_item(item_number="AF-X01-WING", item_name="Wing", item_type="wing")
        change = change_svc.create_change(
            change_type="engineering_change", title="Test", description="Test",
            affected_items=[{"item_id": item.item_id}],
        )
        impact = change_svc.analyze_impact(change.change_id)
        assert len(impact["affected_items"]) == 1


class TestConfigCompatibilityService:
    def test_validate_compatible(self):
        svc = ConfigCompatibilityService()
        items = [
            ConfigItem(item_type="motor", item_number="M1", item_name="Motor"),
            ConfigItem(item_type="esc", item_number="E1", item_name="ESC"),
            ConfigItem(item_type="battery", item_number="B1", item_name="Battery"),
        ]
        result = svc.validate_compatibility(items)
        assert result["is_compatible"] is True

    def test_validate_incompatible(self):
        svc = ConfigCompatibilityService()
        items = [
            ConfigItem(item_type="motor", item_number="M1", item_name="Motor"),
        ]
        result = svc.validate_compatibility(items)
        assert result["is_compatible"] is False
        assert len(result["violations"]) > 0


class TestConfigItemType:
    def test_all_types(self):
        assert len(ConfigItemType.values()) == 15

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError):
            ConfigItemType("invalid")


class TestPropagationAction:
    def test_all_actions(self):
        assert len(PropagationAction) == 8