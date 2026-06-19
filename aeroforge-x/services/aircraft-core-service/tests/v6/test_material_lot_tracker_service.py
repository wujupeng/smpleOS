"""AeroForge-X V6.0/V6.1 Unit Tests - MaterialLotTrackerService
REQ-SUP-007~012, REQ-VP-020
"""

import pytest

from src.domain.services.supplier.material_lot_tracker_service import (
    MaterialLotTrackerService,
    MaterialLot,
    LotStatus,
    GenealogyStep,
    TransformationType,
    ForwardTraceResult,
    BackwardTraceResult,
    ContainmentActionResult,
)


@pytest.fixture
def service():
    return MaterialLotTrackerService()


@pytest.fixture
def lot():
    return MaterialLot(
        lot_id="LOT-001",
        supplier_id="SUP-001",
        material_specification="AMS-4901",
        heat_number="HT-2024-001",
        certificate_of_conformance="COC-001",
    )


class TestReceiveMaterialLot:

    def test_receive_lot(self, service, lot):
        result = service.receiveMaterialLot(lot)
        assert result.lot_id == "LOT-001"
        assert result.status == LotStatus.RECEIVED

    def test_receive_duplicate_raises(self, service, lot):
        service.receiveMaterialLot(lot)
        with pytest.raises(ValueError, match="already exists"):
            service.receiveMaterialLot(lot)


class TestForwardTraceability:

    def test_forward_trace_installed_parts(self, service, lot):
        service.receiveMaterialLot(lot)
        service.registerPartInstallation("LOT-001", "PART-SN-001", "MSN-001")
        result = service.forwardTraceability("LOT-001")
        assert isinstance(result, ForwardTraceResult)
        assert "PART-SN-001" in result.affected_parts
        assert "MSN-001" in result.affected_aircraft

    def test_forward_trace_no_installations(self, service, lot):
        service.receiveMaterialLot(lot)
        result = service.forwardTraceability("LOT-001")
        assert len(result.affected_parts) == 0

    def test_forward_trace_nonexistent_raises(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.forwardTraceability("FAKE-LOT")


class TestBackwardTraceability:

    def test_backward_trace(self, service, lot):
        service.receiveMaterialLot(lot)
        service.registerPartInstallation("LOT-001", "PART-SN-001", "MSN-001")
        result = service.backwardTraceability("PART-SN-001")
        assert isinstance(result, BackwardTraceResult)
        assert result.material_lot is not None
        assert result.supplier_id == "SUP-001"

    def test_backward_trace_unknown_part(self, service):
        result = service.backwardTraceability("UNKNOWN-PART")
        assert result.material_lot is None


class TestNonConformingLot:

    def test_flag_non_conforming(self, service, lot):
        service.receiveMaterialLot(lot)
        service.registerPartInstallation("LOT-001", "PART-SN-001", "MSN-001")
        result = service.flagNonConformingLot("LOT-001")
        assert isinstance(result, ContainmentActionResult)
        assert result.affected_parts_count > 0
        assert len(result.containment_actions) > 0
        lot_obj = service.getLot("LOT-001")
        assert lot_obj.status == LotStatus.NON_CONFORMING

    def test_flag_non_conforming_with_aircraft(self, service, lot):
        service.receiveMaterialLot(lot)
        service.registerPartInstallation("LOT-001", "PART-SN-001", "MSN-001")
        result = service.flagNonConformingLot("LOT-001")
        assert "MSN-001" in result.affected_aircraft


class TestGenealogy:

    def test_record_genealogy_step(self, service, lot):
        service.receiveMaterialLot(lot)
        lot2 = MaterialLot(lot_id="LOT-002", supplier_id="SUP-001",
                           material_specification="AMS-4901", heat_number="HT-002")
        service.receiveMaterialLot(lot2)
        step = GenealogyStep(
            step_id="", lot_id="LOT-001",
            transformation_type=TransformationType.INGOT_TO_BILLET,
            output_lot_id="LOT-002",
        )
        result = service.recordGenealogyStep(step)
        assert result.step_id.startswith("GEN-")

    def test_genealogy_nonexistent_lot_raises(self, service):
        step = GenealogyStep(step_id="", lot_id="FAKE-LOT",
                             transformation_type=TransformationType.INGOT_TO_BILLET)
        with pytest.raises(ValueError, match="not found"):
            service.recordGenealogyStep(step)


class TestPartInstallation:

    def test_register_part_installation(self, service, lot):
        service.receiveMaterialLot(lot)
        service.registerPartInstallation("LOT-001", "PART-SN-001", "MSN-001")
        lot_obj = service.getLot("LOT-001")
        assert "PART-SN-001" in lot_obj.installed_parts
        assert "MSN-001" in lot_obj.installed_aircraft
        assert lot_obj.status == LotStatus.INSTALLED

    def test_register_duplicate_part_ignored(self, service, lot):
        service.receiveMaterialLot(lot)
        service.registerPartInstallation("LOT-001", "PART-SN-001", "MSN-001")
        service.registerPartInstallation("LOT-001", "PART-SN-001", "MSN-001")
        lot_obj = service.getLot("LOT-001")
        assert lot_obj.installed_parts.count("PART-SN-001") == 1