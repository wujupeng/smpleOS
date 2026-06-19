"""AeroForge-X V6.0/V6.1 Unit Tests - Configuration Manager Service
REQ-VP-020, REQ-CFG-001~006
"""

import pytest

from src.domain.services.configuration_management.configuration_manager_service import (
    ConfigurationManagerService,
    BlockConfiguration,
    SerialNumberConfiguration,
    ConfigViewType,
    ConflictType,
)


@pytest.fixture
def service():
    return ConfigurationManagerService()


class TestBlockConfiguration:

    def test_create_block_config(self, service):
        block = service.createBlockConfig("A320", "Block-1")
        assert block.block_id == "BLK-A320-Block-1"
        assert block.aircraft_type == "A320"
        assert block.block_name == "Block-1"
        assert block.design_config is not None

    def test_create_block_config_duplicate_raises(self, service):
        service.createBlockConfig("A320", "Block-1")
        with pytest.raises(ValueError, match="already exists"):
            service.createBlockConfig("A320", "Block-1")

    def test_create_multiple_blocks(self, service):
        b1 = service.createBlockConfig("A320", "Block-1")
        b2 = service.createBlockConfig("A320", "Block-2")
        assert b1.block_id != b2.block_id


class TestSNConfiguration:

    def test_create_sn_config(self, service):
        block = service.createBlockConfig("A320", "Block-1")
        sn = service.createSNConfig(block.block_id, "MSN-001")
        assert sn.sn_id == "SN-MSN-001"
        assert sn.tail_number == "MSN-001"
        assert sn.block_id == block.block_id

    def test_create_sn_inherits_design_config(self, service):
        block = service.createBlockConfig("A320", "Block-1")
        sn = service.createSNConfig(block.block_id, "MSN-001")
        assert sn.design_config is not None

    def test_create_sn_nonexistent_block_raises(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.createSNConfig("BLK-FAKE", "MSN-001")

    def test_create_sn_duplicate_raises(self, service):
        block = service.createBlockConfig("A320", "Block-1")
        service.createSNConfig(block.block_id, "MSN-001")
        with pytest.raises(ValueError, match="already exists"):
            service.createSNConfig(block.block_id, "MSN-001")


class TestConfigHierarchy:

    def test_get_hierarchy(self, service):
        service.createBlockConfig("A320", "Block-1")
        hierarchy = service.getConfigHierarchy("A320")
        assert hierarchy.aircraft_type == "A320"
        assert len(hierarchy.blocks) == 1

    def test_get_hierarchy_nonexistent_raises(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.getConfigHierarchy("FAKE")


class TestBlockInheritance:

    def test_inherit_block_config(self, service):
        source = service.createBlockConfig("A320", "Block-1")
        new_block = service.inheritBlockConfig("Block-2", source.block_id, {})
        assert new_block.block_id != source.block_id
        assert new_block.design_config is not None

    def test_inherit_block_nonexistent_raises(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.inheritBlockConfig("Block-2", "BLK-FAKE", {})


class TestConflictDetection:

    def test_detect_conflicts_no_conflict(self, service):
        block = service.createBlockConfig("A320", "Block-1")
        sn = service.createSNConfig(block.block_id, "MSN-001")
        report = service.detectConfigConflicts(block.block_id, sn.sn_id)
        assert len(report.conflicts) == 0

    def test_detect_conflicts_nonexistent_raises(self, service):
        with pytest.raises(ValueError):
            service.detectConfigConflicts("BLK-FAKE", "SN-FAKE")