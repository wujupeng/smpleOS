"""AeroForge-X V6.1 Integration Tests - Material Traceability E2E
IT-F03: receiveLot → recordGenealogy → forwardTrace → backwardTrace
REQ-VP-047
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "aircraft-core-service"))

import pytest

from src.domain.services.supplier.material_lot_tracker_service import (
    MaterialLotTrackerService, MaterialLot, GenealogyStep, TransformationType,
)


@pytest.fixture
def service():
    return MaterialLotTrackerService()


class TestMaterialTraceabilityE2E:

    def test_full_traceability_chain(self, service):
        ingot = MaterialLot(
            lot_id="LOT-INGOT", supplier_id="SUP-001",
            material_specification="AMS-4901", heat_number="HT-001",
        )
        service.receiveMaterialLot(ingot)

        billet = MaterialLot(
            lot_id="LOT-BILLET", supplier_id="SUP-001",
            material_specification="AMS-4901", heat_number="HT-001",
        )
        service.receiveMaterialLot(billet)

        forging = MaterialLot(
            lot_id="LOT-FORGING", supplier_id="SUP-001",
            material_specification="AMS-4901", heat_number="HT-001",
        )
        service.receiveMaterialLot(forging)

        step1 = GenealogyStep(
            step_id="", lot_id="LOT-INGOT",
            transformation_type=TransformationType.INGOT_TO_BILLET,
            output_lot_id="LOT-BILLET",
        )
        service.recordGenealogyStep(step1)

        step2 = GenealogyStep(
            step_id="", lot_id="LOT-BILLET",
            transformation_type=TransformationType.BILLET_TO_FORGING,
            output_lot_id="LOT-FORGING",
        )
        service.recordGenealogyStep(step2)

        service.registerPartInstallation("LOT-FORGING", "PART-SN-001", "MSN-001")

        forward = service.forwardTraceability("LOT-INGOT")
        assert "PART-SN-001" in forward.affected_parts
        assert "MSN-001" in forward.affected_aircraft

        backward = service.backwardTraceability("PART-SN-001")
        assert backward.material_lot is not None
        assert backward.supplier_id == "SUP-001"
        assert backward.certification_data.get("heat_number") == "HT-001"

    def test_non_conforming_lot_containment(self, service):
        lot = MaterialLot(
            lot_id="LOT-NC", supplier_id="SUP-001",
            material_specification="AMS-4901", heat_number="HT-NC",
        )
        service.receiveMaterialLot(lot)
        service.registerPartInstallation("LOT-NC", "PART-NC-001", "MSN-002")

        containment = service.flagNonConformingLot("LOT-NC")
        assert len(containment.containment_actions) > 0
        assert "MSN-002" in containment.affected_aircraft