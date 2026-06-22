"""AeroForge-X V6.1 Integration Tests - Configuration Baseline Lifecycle
IT-E02: establishFBL → establishFCL → establishFSDL → submitChange → impactAnalysis → approve → implement → verify → baselineUpdate
REQ-VP-043
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "aircraft-core-service"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "workflow-engine-service"))

import pytest

from src.domain.services.configuration_management.configuration_manager_service import ConfigurationManagerService
from src.domain.services.configuration_management.configuration_baseline_service import (
    ConfigurationBaselineService,
    BaselineType,
)
from src.domain.services.configuration_management.configuration_change_control_service import (
    ConfigurationChangeControlService,
    ConfigurationChangeRequest,
    ChangeClass,
    ChangeRequestStatus,
)


@pytest.fixture
def config_mgr():
    return ConfigurationManagerService()


@pytest.fixture
def baseline_svc():
    return ConfigurationBaselineService()


@pytest.fixture
def change_ctrl_svc():
    return ConfigurationChangeControlService()


class TestConfigBaselineLifecycle:

    @pytest.mark.asyncio
    async def test_full_baseline_lifecycle(self, config_mgr, baseline_svc, change_ctrl_svc):
        block = await config_mgr.createBlockConfig("A320", "Block-1")

        fbl = await baseline_svc.establishFBL(block, "engineer-1")
        assert fbl.baseline_type == BaselineType.FBL
        assert fbl.locked is True

        fcl = await baseline_svc.establishFCL(block, "engineer-2")
        assert fcl.baseline_type == BaselineType.FCL

        fsdl = await baseline_svc.establishFSDL(block, "engineer-3")
        assert fsdl.baseline_type == BaselineType.FSDL

        cr = ConfigurationChangeRequest(
            request_id="CR-001",
            block_id=block.block_id,
            change_class=ChangeClass.CLASS_I,
            change_type="DesignChange",
            description="Wing modification",
            requested_by="engineer-1",
            affected_items=[{"item_id": "item-1", "affected_views": ["Design"], "affected_sns": []}],
        )
        change_ctrl_svc.submitChangeRequest(cr)
        assert cr.status == ChangeRequestStatus.SUBMITTED

        impact = change_ctrl_svc.performImpactAnalysis("CR-001")
        assert len(impact.affected_design_items) > 0

        approval = change_ctrl_svc.approveChangeRequest("CR-001", "Chief-Engineer", ChangeClass.CLASS_I)
        assert approval.approved is True

        impl = change_ctrl_svc.implementChange("CR-001")
        assert impl.propagation_completed is True

        verify = change_ctrl_svc.verifyChange("CR-001")
        assert verify.is_verified is True

        await baseline_svc.trackBaselineChanges(
            fsdl.baseline_id, "CR-001", "DesignChange", "Chief-Engineer", ["item-1"]
        )
        updated_fsdl = await baseline_svc.getBaseline(fsdl.baseline_id)
        assert len(updated_fsdl.change_history) == 1
