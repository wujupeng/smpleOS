"""AeroForge-X V6.1 Integration Tests - Supplier Quality Lifecycle
IT-F02: registerSupplier → computeRating → receiveLot → recordNDT → createIssue → createCAR → verifyCAR → updateRating
REQ-VP-046
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "aircraft-core-service"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "workflow-engine-service"))

import pytest

from src.domain.services.supplier.supplier_registry_service import (
    SupplierRegistryService, SupplierProfile, SupplierStatus,
)
from src.domain.services.supplier.material_lot_tracker_service import (
    MaterialLotTrackerService, MaterialLot,
)
from src.domain.services.supplier.ndt_integration_service import (
    NDTIntegrationService, NDTRecord, NDTMethod, NDTResult,
)
from src.domain.services.supplier.supplier_car_service import (
    SupplierCARService, QualityIssue, CARSeverity,
)


@pytest.fixture
def registry():
    return SupplierRegistryService()


@pytest.fixture
def lot_tracker():
    return MaterialLotTrackerService()


@pytest.fixture
def ndt_svc():
    return NDTIntegrationService()


@pytest.fixture
def car_svc():
    return SupplierCARService()


class TestSupplierQualityLifecycle:

    def test_full_supplier_quality_lifecycle(self, registry, lot_tracker, ndt_svc, car_svc):
        profile = SupplierProfile(
            supplier_id="SUP-001",
            company_name="AeroParts Inc.",
            certifications=["AS9100"],
            approved_parts=["PART-A"],
        )
        registry.registerSupplier(profile)
        assert registry.getSupplier("SUP-001").status == SupplierStatus.PENDING

        for _ in range(4):
            registry.approveSupplierWorkflow("SUP-001")
        assert registry.getSupplier("SUP-001").status == SupplierStatus.APPROVED

        registry.updateRatingMetrics(
            "SUP-001", on_time_delivery_rate=0.95, first_pass_yield=0.98,
            defect_rate=0.01, car_responsiveness=0.90, audit_findings_score=0.95,
        )
        rating = registry.computeQualityRating("SUP-001")
        assert rating.overall_rating >= 70

        lot = MaterialLot(
            lot_id="LOT-001", supplier_id="SUP-001",
            material_specification="AMS-4901", heat_number="HT-001",
        )
        lot_tracker.receiveMaterialLot(lot)

        ndt = NDTRecord(
            ndt_id="NDT-001", part_id="PART-A",
            inspection_method=NDTMethod.UT, result=NDTResult.REJECT,
            linked_lot_id="LOT-001",
        )
        ndt_svc.importNDTRecord(ndt)
        fracas = ndt_svc.handleRejectResult("NDT-001")
        assert fracas.disposition_process_started is True

        issue = car_svc.createQualityIssue(
            "SUP-001", "PART-A", "UT rejection - crack detected", "LOT-001"
        )
        assert issue.supplier_id == "SUP-001"

        car = car_svc.createCAR(issue.issue_id, CARSeverity.MAJOR, "Lead-QA-1")
        assert car.car_id.startswith("CAR-")

        car_svc.verifyCAR(car.car_id, "Corrective action implemented", "QA-Manager-1", True)

        registry.updateRatingMetrics("SUP-001", defect_rate=0.05)
        updated_rating = registry.computeQualityRating("SUP-001")
        assert updated_rating.defect_rate == 0.05