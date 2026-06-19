"""AeroForge-X V6.0/V6.1 Unit Tests - ThreeViewConfigPropagationService
REQ-CFG-007~011, REQ-VP-020
"""

import pytest

from src.domain.services.configuration_management.three_view_config_propagation_service import (
    ThreeViewConfigPropagationService,
    ManufacturingRule,
    OperationalRule,
    DesignConfigChange,
    PropagationResult,
    ReconciliationReport,
)
from src.domain.services.configuration_management.configuration_manager_service import (
    ConfigurationManagerService,
    ConfigViewType,
    ConfigurationItem,
)


@pytest.fixture
def config_mgr():
    return ConfigurationManagerService()


@pytest.fixture
def service():
    return ThreeViewConfigPropagationService()


@pytest.fixture
def block_with_design(config_mgr):
    return config_mgr.createBlockConfig("A320", "Block-1")


class TestManufacturingDerivation:

    def test_derive_manufacturing_config(self, service, block_with_design):
        mfg = service.deriveManufacturingConfig(block_with_design.design_config)
        assert mfg.config_id.startswith("MC-")
        assert mfg.source_design_config_id == block_with_design.design_config.config_id
        assert mfg.status == "Active"

    def test_derive_with_custom_rules(self, service, block_with_design):
        rule = ManufacturingRule(
            rule_id="R1", rule_type="ProcessAssignment",
            rule_expression="CNC-Milling", priority=1
        )
        mfg = service.deriveManufacturingConfig(
            block_with_design.design_config, rules=[rule]
        )
        assert mfg.manufacturing_rules_applied == ["R1"]
        for item in mfg.configuration_items:
            assert item.value.get("assigned_process") == "CNC-Milling"

    def test_derive_with_tooling_rule(self, service, block_with_design):
        rule = ManufacturingRule(
            rule_id="R2", rule_type="ToolingReference",
            rule_expression="FIX-A01", priority=1
        )
        mfg = service.deriveManufacturingConfig(
            block_with_design.design_config, rules=[rule]
        )
        for item in mfg.configuration_items:
            assert item.value.get("tooling_ref") == "FIX-A01"


class TestOperationalDerivation:

    def test_derive_operational_config(self, service, block_with_design):
        mfg = service.deriveManufacturingConfig(block_with_design.design_config)
        op = service.deriveOperationalConfig(mfg)
        assert op.config_id.startswith("OC-")
        assert op.source_mfg_config_id == mfg.config_id
        assert op.status == "Active"

    def test_derive_with_equipment_rule(self, service, block_with_design):
        mfg = service.deriveManufacturingConfig(block_with_design.design_config)
        rule = OperationalRule(
            rule_id="OP1", rule_type="EquipmentInstallation",
            rule_expression="AVIONICS-BAY-1", priority=1
        )
        op = service.deriveOperationalConfig(mfg, rules=[rule])
        for item in op.configuration_items:
            assert item.value.get("equipment_install") == "AVIONICS-BAY-1"


class TestDesignChangePropagation:

    def test_propagate_design_change(self, service, config_mgr):
        block = config_mgr.createBlockConfig("A320", "Block-1")
        change = DesignConfigChange(
            block_id=block.block_id,
            changed_items=[{"item_id": block.design_config.configuration_items[0].item_id, "new_values": {"thickness": 5.0}}],
            change_reason="Structural reinforcement",
        )
        result = service.propagateDesignChange(block, change)
        assert result.design_updated is True
        assert result.manufacturing_updated is True
        assert result.operational_updated is True
        assert result.propagation_duration_ms >= 0

    def test_propagate_no_design_config(self, service, config_mgr):
        block = config_mgr.createBlockConfig("A320", "Block-1")
        block.design_config = None
        change = DesignConfigChange(
            block_id=block.block_id,
            changed_items=[],
            change_reason="test",
        )
        result = service.propagateDesignChange(block, change)
        assert result.design_updated is False
        assert result.manufacturing_updated is False


class TestRuleRegistration:

    def test_register_manufacturing_rule(self, service):
        rule = ManufacturingRule(
            rule_id="R1", rule_type="ProcessAssignment",
            rule_expression="CNC", priority=5
        )
        service.registerManufacturingRule(rule)
        assert len(service._mfg_rules) == 1

    def test_rules_sorted_by_priority(self, service):
        r1 = ManufacturingRule(rule_id="R1", rule_type="ProcessAssignment", rule_expression="A", priority=1)
        r2 = ManufacturingRule(rule_id="R2", rule_type="ProcessAssignment", rule_expression="B", priority=10)
        service.registerManufacturingRule(r1)
        service.registerManufacturingRule(r2)
        assert service._mfg_rules[0].rule_id == "R2"


class TestInconsistencyDetection:

    def test_detect_no_inconsistencies(self, service, config_mgr):
        block = config_mgr.createBlockConfig("A320", "Block-1")
        service.deriveManufacturingConfig(block.design_config)
        if block.design_config:
            service.deriveOperationalConfig(block.manufacturing_config)
        report = service.detectInconsistencies(block)
        assert isinstance(report, ReconciliationReport)

    def test_detect_missing_views(self, service, config_mgr):
        block = config_mgr.createBlockConfig("A320", "Block-1")
        report = service.detectInconsistencies(block)
        assert len(report.reconciliation_suggestions) > 0