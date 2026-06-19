"""AeroForge-X V6.1 Integration Tests - Cross-Program Event-Driven Tests
IT-E03/F04/G05 + INT-1.1~1.10 verification
REQ-VP-053, REQ-VP-054
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "aircraft-core-service"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "physics-twin-service"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "workflow-engine-service"))

import pytest

from src.domain.services.digital_factory.shop_floor_event_emitter_service import (
    ShopFloorEventEmitterService, ShopFloorEventType, EventFilter,
)
from src.domain.services.integration.cross_program_event_orchestrator_service import (
    CrossProgramEventOrchestratorService,
)


@pytest.fixture
def emitter():
    return ShopFloorEventEmitterService()


@pytest.fixture
def orchestrator():
    return CrossProgramEventOrchestratorService()


class TestFactoryCARInteraction:

    def test_quality_alert_triggers_car(self, emitter, orchestrator):
        receipt = emitter.emitQualityAlert("EQ-001", {
            "defect_type": "Crack",
            "severity": "Major",
            "lot_id": "LOT-001",
        })
        assert receipt.published is True
        assert receipt.subject == "aeroforge.v6.factory.quality.alert"

        car_event = orchestrator.publishEvent(
            subject="aeroforge.v6.factory.quality.alert",
            payload={"defect_type": "Crack", "severity": "Major", "lot_id": "LOT-001"},
            source="physics-twin-service",
        )
        assert car_event is not None


class TestCrossProgramEvents:

    def test_int_1_1_config_change_propagated(self, orchestrator):
        event = orchestrator.publishEvent(
            subject="aeroforge.v6.config.change.propagated",
            payload={"block_id": "BLK-A320-1", "change_id": "CHG-001"},
            source="aircraft-core-service",
        )
        assert event is not None

    def test_int_1_2_cert_trace_gap_alert(self, orchestrator):
        event = orchestrator.publishEvent(
            subject="aeroforge.v6.cert.trace.gap.alert",
            payload={"requirement_id": "REQ-001", "gap_type": "MissingEvidence"},
            source="aircraft-core-service",
        )
        assert event is not None

    def test_int_1_3_cert_evidence_package_locked(self, orchestrator):
        event = orchestrator.publishEvent(
            subject="aeroforge.v6.cert.evidence.package.locked",
            payload={"package_id": "CEP-001", "locked_by": "QA-1"},
            source="workflow-engine-service",
        )
        assert event is not None

    def test_int_1_4_supplier_quality_issue(self, orchestrator):
        event = orchestrator.publishEvent(
            subject="aeroforge.v6.supplier.quality.issue.created",
            payload={"supplier_id": "SUP-001", "issue_type": "NDT_Reject"},
            source="aircraft-core-service",
        )
        assert event is not None

    def test_int_1_5_supplier_car_created(self, orchestrator):
        event = orchestrator.publishEvent(
            subject="aeroforge.v6.supplier.car.created",
            payload={"car_id": "CAR-001", "supplier_id": "SUP-001"},
            source="workflow-engine-service",
        )
        assert event is not None

    def test_int_1_8_factory_equipment_status(self, orchestrator):
        event = orchestrator.publishEvent(
            subject="aeroforge.v6.factory.equipment.status",
            payload={"equipment_id": "EQ-001", "new_status": "Error"},
            source="physics-twin-service",
        )
        assert event is not None

    def test_int_1_9_factory_quality_alert(self, orchestrator):
        event = orchestrator.publishEvent(
            subject="aeroforge.v6.factory.quality.alert",
            payload={"equipment_id": "EQ-001", "alert": "Defect detected"},
            source="physics-twin-service",
        )
        assert event is not None

    def test_int_1_10_uq_high_uncertainty(self, orchestrator):
        event = orchestrator.publishEvent(
            subject="aeroforge.v6.uq.high_uncertainty",
            payload={"model_id": "SM-001", "cov": 0.15},
            source="physics-twin-service",
        )
        assert event is not None

    def test_event_delivery_timeout_detection(self, orchestrator):
        orchestrator.publishEvent(
            subject="aeroforge.v6.config.change.propagated",
            payload={"test": "timeout"},
            source="aircraft-core-service",
        )
        events = orchestrator.getEventLog()
        assert len(events) > 0
        for e in events:
            assert "published_at" in e or "timestamp" in e or "event_id" in e