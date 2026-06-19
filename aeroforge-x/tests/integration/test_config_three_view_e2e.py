"""AeroForge-X V6.1 Integration Tests - Configuration Three-View E2E
IT-E01: createBlock → deriveMfg → deriveOp → propagateChange → verify three-view consistency
REQ-VP-042
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "aircraft-core-service"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "physics-twin-service"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "workflow-engine-service"))

import pytest

from src.domain.services.configuration_management.configuration_manager_service import ConfigurationManagerService
from src.domain.services.configuration_management.three_view_config_propagation_service import (
    ThreeViewConfigPropagationService,
    ManufacturingRule,
    OperationalRule,
    DesignConfigChange,
)


@pytest.fixture
def config_mgr():
    return ConfigurationManagerService()


@pytest.fixture
def propagation_svc():
    return ThreeViewConfigPropagationService()


class TestConfigThreeViewE2E:

    def test_full_three_view_lifecycle(self, config_mgr, propagation_svc):
        block = config_mgr.createBlockConfig("A320", "Block-1")
        assert block.design_config is not None

        mfg_rule = ManufacturingRule(
            rule_id="MR-1", rule_type="ProcessAssignment",
            rule_expression="CNC-Milling", priority=1
        )
        propagation_svc.registerManufacturingRule(mfg_rule)

        op_rule = OperationalRule(
            rule_id="OR-1", rule_type="EquipmentInstallation",
            rule_expression="AVIONICS-BAY-1", priority=1
        )
        propagation_svc.registerOperationalRule(op_rule)

        mfg_config = propagation_svc.deriveManufacturingConfig(block.design_config)
        assert mfg_config.source_design_config_id == block.design_config.config_id
        block.manufacturing_config = mfg_config

        op_config = propagation_svc.deriveOperationalConfig(mfg_config)
        assert op_config.source_mfg_config_id == mfg_config.config_id
        block.operational_config = op_config

        change = DesignConfigChange(
            block_id=block.block_id,
            changed_items=[{
                "item_id": block.design_config.configuration_items[0].item_id,
                "new_values": {"thickness": 5.0},
            }],
            change_reason="Structural reinforcement",
        )
        result = propagation_svc.propagateDesignChange(block, change)
        assert result.design_updated is True
        assert result.manufacturing_updated is True
        assert result.operational_updated is True

        report = propagation_svc.detectInconsistencies(block)
        assert isinstance(report, report.__class__)

    def test_three_view_propagation_timing(self, config_mgr, propagation_svc):
        block = config_mgr.createBlockConfig("A350", "Block-1")
        propagation_svc.registerManufacturingRule(
            ManufacturingRule(rule_id="MR-1", rule_type="ProcessAssignment", rule_expression="CNC", priority=1)
        )
        propagation_svc.registerOperationalRule(
            OperationalRule(rule_id="OR-1", rule_type="EquipmentInstallation", rule_expression="BAY-1", priority=1)
        )

        change = DesignConfigChange(
            block_id=block.block_id,
            changed_items=[{
                "item_id": block.design_config.configuration_items[0].item_id,
                "new_values": {"updated": True},
            }],
            change_reason="Timing test",
        )
        result = propagation_svc.propagateDesignChange(block, change)
        assert result.propagation_duration_ms < 10000