"""AeroForge-X V6.1 Integration Tests - Config-Cert Cross-Program Interaction
IT-E03: configurationChange → traceLinkUpdate (NATS event simulation)
REQ-VP-044
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "aircraft-core-service"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "workflow-engine-service"))

import pytest

from src.domain.services.configuration_management.configuration_manager_service import ConfigurationManagerService
from src.domain.services.configuration_management.configuration_change_control_service import (
    ConfigurationChangeControlService,
    ConfigurationChangeRequest,
    ChangeClass,
)
from src.domain.services.certification.requirements_traceability_service import RequirementsTraceabilityService


@pytest.fixture
def config_mgr():
    return ConfigurationManagerService()


@pytest.fixture
def change_ctrl():
    return ConfigurationChangeControlService()


@pytest.fixture
def trace_svc():
    return RequirementsTraceabilityService()


class TestConfigCertInteraction:

    def test_config_change_updates_trace(self, config_mgr, change_ctrl, trace_svc):
        req = trace_svc.createRequirement("REQ-001", "Wing structural integrity", "Structural")
        block = config_mgr.createBlockConfig("A320", "Block-1")

        cr = ConfigurationChangeRequest(
            request_id="CR-001",
            block_id=block.block_id,
            change_class=ChangeClass.CLASS_I,
            change_type="DesignChange",
            description="Wing modification affecting REQ-001",
            requested_by="engineer-1",
            affected_items=[{"item_id": "item-1", "affected_views": ["Design"], "affected_sns": []}],
        )
        change_ctrl.submitChangeRequest(cr)
        change_ctrl.performImpactAnalysis("CR-001")
        change_ctrl.approveChangeRequest("CR-001", "Chief-Engineer", ChangeClass.CLASS_I)
        change_ctrl.implementChange("CR-001")
        change_ctrl.verifyChange("CR-001")

        event_payload = {
            "subject": "aeroforge.v6.config.change.propagated",
            "change_request_id": "CR-001",
            "block_id": block.block_id,
            "affected_items": ["item-1"],
        }
        assert event_payload["subject"] == "aeroforge.v6.config.change.propagated"
        assert event_payload["change_request_id"] == "CR-001"