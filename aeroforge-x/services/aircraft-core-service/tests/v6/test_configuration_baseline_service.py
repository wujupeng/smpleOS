"""AeroForge-X V6.0/V6.1 Unit Tests - ConfigurationBaselineService
REQ-CFG-012~017, REQ-VP-020
"""

import pytest

from src.domain.services.configuration_management.configuration_baseline_service import (
    ConfigurationBaselineService,
    BaselineType,
    BaselineMilestone,
    ConfigurationBaseline,
    BaselineDeltaReport,
)
from src.domain.services.configuration_management.configuration_manager_service import (
    ConfigurationManagerService,
)


@pytest.fixture
def config_mgr():
    return ConfigurationManagerService()


@pytest.fixture
def service():
    return ConfigurationBaselineService()


@pytest.fixture
def block(config_mgr):
    return config_mgr.createBlockConfig("A320", "Block-1")


class TestEstablishBaselines:

    def test_establish_fbl(self, service, block):
        baseline = service.establishFBL(block, "engineer-1")
        assert baseline.baseline_type == BaselineType.FBL
        assert baseline.milestone == BaselineMilestone.SRR.value
        assert baseline.locked is True
        assert baseline.established_by == "engineer-1"

    def test_establish_fcl(self, service, block):
        baseline = service.establishFCL(block, "engineer-2")
        assert baseline.baseline_type == BaselineType.FCL
        assert baseline.milestone == BaselineMilestone.PDR.value

    def test_establish_fsdl(self, service, block):
        baseline = service.establishFSDL(block, "engineer-3")
        assert baseline.baseline_type == BaselineType.FSDL
        assert baseline.milestone == BaselineMilestone.CDR.value

    def test_baseline_has_frozen_items(self, service, block):
        baseline = service.establishFBL(block, "engineer-1")
        assert len(baseline.frozen_items) > 0

    def test_baseline_has_snapshot(self, service, block):
        baseline = service.establishFBL(block, "engineer-1")
        assert baseline.configuration_snapshot is not None

    def test_block_locked_after_baseline(self, service, block):
        service.establishFBL(block, "engineer-1")
        assert block.locked is True


class TestFreezeBaseline:

    def test_freeze_baseline(self, service, block):
        baseline = service.establishFBL(block, "engineer-1")
        baseline.locked = False
        result = service.freezeBaselineItems(baseline.baseline_id)
        assert result.locked is True

    def test_freeze_nonexistent_raises(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.freezeBaselineItems("FAKE-ID")


class TestTrackChanges:

    def test_track_baseline_changes(self, service, block):
        baseline = service.establishFBL(block, "engineer-1")
        record = service.trackBaselineChanges(
            baseline.baseline_id, "CR-001", "DesignChange", "Chief-1", ["item-1"]
        )
        assert record.change_id.startswith("BCR-")
        assert record.change_request_id == "CR-001"
        assert record.change_type == "DesignChange"
        assert len(baseline.change_history) == 1

    def test_track_nonexistent_raises(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.trackBaselineChanges("FAKE", "CR-001", "Type", "A", [])


class TestCompareBaselines:

    def test_compare_identical_baselines(self, service, block):
        b1 = service.establishFBL(block, "engineer-1")
        b2 = service.establishFCL(block, "engineer-2")
        report = service.compareBaselines(b1.baseline_id, b2.baseline_id)
        assert isinstance(report, BaselineDeltaReport)

    def test_compare_nonexistent_raises(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.compareBaselines("FAKE-1", "FAKE-2")


class TestGetBaseline:

    def test_get_existing_baseline(self, service, block):
        baseline = service.establishFBL(block, "engineer-1")
        result = service.getBaseline(baseline.baseline_id)
        assert result is not None
        assert result.baseline_id == baseline.baseline_id

    def test_get_nonexistent_returns_none(self, service):
        result = service.getBaseline("FAKE-ID")
        assert result is None