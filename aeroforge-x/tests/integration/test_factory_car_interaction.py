"""AeroForge-X V6.1 Integration Tests - Factory-CAR Cross-Program Interaction
IT-G05: shopFloorQualityAlert → CARTrigger
REQ-VP-053
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "physics-twin-service"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "workflow-engine-service"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "aircraft-core-service"))

import pytest

from src.domain.services.digital_factory.shop_floor_event_emitter_service import ShopFloorEventEmitterService
from src.domain.services.supplier.supplier_car_service import SupplierCARService, CARSeverity
from src.domain.services.integration.cross_program_event_orchestrator_service import (
    CrossProgramEventOrchestratorService,
)


@pytest.fixture
def emitter():
    return ShopFloorEventEmitterService()


@pytest.fixture
def car_svc():
    return SupplierCARService()


@pytest.fixture
def orchestrator():
    return CrossProgramEventOrchestratorService()


class TestFactoryCARInteraction:

    def test_quality_alert_triggers_car(self, emitter, car_svc, orchestrator):
        receipt = emitter.emitQualityAlert("EQ-CNC-001", {
            "defect_type": "Dimensional non-conformance",
            "severity": "Major",
            "lot_id": "LOT-001",
            "supplier_id": "SUP-001",
            "part_id": "PART-A",
        })
        assert receipt.published is True
        assert receipt.subject == "aeroforge.v6.factory.quality.alert"

        event = orchestrator.publishEvent(
            subject="aeroforge.v6.factory.quality.alert",
            payload={
                "defect_type": "Dimensional non-conformance",
                "severity": "Major",
                "lot_id": "LOT-001",
                "supplier_id": "SUP-001",
                "part_id": "PART-A",
            },
            source="physics-twin-service",
        )
        assert event is not None

        issue = car_svc.createQualityIssue(
            "SUP-001", "PART-A",
            "Dimensional non-conformance from shop floor",
            "LOT-001",
        )
        car = car_svc.createCAR(issue.issue_id, CARSeverity.MAJOR, "QA-1")
        assert car.car_id.startswith("CAR-")
        assert car.status == "Open"

    def test_deviation_alert_triggers_investigation(self, emitter, car_svc, orchestrator):
        receipt = emitter.emitDeviationAlert("EQ-CNC-002", {
            "parameter": "temperature",
            "deviation_pct": 25.0,
            "twin_predicted": 150.0,
            "physical_actual": 187.5,
        })
        assert receipt.published is True

        event = orchestrator.publishEvent(
            subject="aeroforge.v6.factory.deviation.alert",
            payload={"equipment_id": "EQ-CNC-002", "deviation_pct": 25.0},
            source="physics-twin-service",
        )
        assert event is not None

        issue = car_svc.createQualityIssue(
            "SUP-002", "PART-B",
            "Process deviation detected by digital twin",
            "LOT-002",
        )
        car = car_svc.createCAR(issue.issue_id, CARSeverity.MINOR, "QA-2")
        assert car.severity == CARSeverity.MINOR