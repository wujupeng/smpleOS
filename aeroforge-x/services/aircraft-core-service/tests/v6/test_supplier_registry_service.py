"""AeroForge-X V6.0/V6.1 Unit Tests - SupplierRegistryService
REQ-SUP-001~006, REQ-VP-020
"""

import pytest

from src.domain.services.supplier.supplier_registry_service import (
    SupplierRegistryService,
    SupplierProfile,
    SupplierStatus,
    ApprovalStage,
    SupplierQualityRating,
    SupplierApprovalWorkflow,
    SuspensionResult,
    SupplyChainImpactReport,
)


@pytest.fixture
def service():
    return SupplierRegistryService()


@pytest.fixture
def supplier_profile():
    return SupplierProfile(
        supplier_id="SUP-001",
        company_name="AeroParts Inc.",
        certifications=["AS9100", "NADCAP"],
        approved_parts=["PART-A", "PART-B"],
    )


class TestRegisterSupplier:

    def test_register_supplier(self, service, supplier_profile):
        result = service.registerSupplier(supplier_profile)
        assert result.supplier_id == "SUP-001"
        assert result.status == SupplierStatus.PENDING

    def test_register_duplicate_raises(self, service, supplier_profile):
        service.registerSupplier(supplier_profile)
        with pytest.raises(ValueError, match="already registered"):
            service.registerSupplier(supplier_profile)

    def test_register_creates_workflow(self, service, supplier_profile):
        service.registerSupplier(supplier_profile)
        wf = service._workflows.get("SUP-001")
        assert wf is not None
        assert wf.current_stage == ApprovalStage.APPLICATION


class TestApprovalWorkflow:

    def test_advance_workflow(self, service, supplier_profile):
        service.registerSupplier(supplier_profile)
        wf = service.approveSupplierWorkflow("SUP-001")
        assert wf.current_stage == ApprovalStage.CAPABILITY_ASSESSMENT

    def test_full_approval_workflow(self, service, supplier_profile):
        service.registerSupplier(supplier_profile)
        stages = list(ApprovalStage)
        for i in range(4):
            service.approveSupplierWorkflow("SUP-001")
        supplier = service.getSupplier("SUP-001")
        assert supplier.status == SupplierStatus.APPROVED

    def test_workflow_nonexistent_raises(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.approveSupplierWorkflow("FAKE-SUP")


class TestQualityRating:

    def test_compute_quality_rating(self, service, supplier_profile):
        service.registerSupplier(supplier_profile)
        rating = service.computeQualityRating("SUP-001")
        assert isinstance(rating, SupplierQualityRating)
        assert rating.overall_rating >= 0

    def test_high_quality_rating(self, service, supplier_profile):
        service.registerSupplier(supplier_profile)
        service.updateRatingMetrics(
            "SUP-001",
            on_time_delivery_rate=0.95,
            first_pass_yield=0.98,
            defect_rate=0.01,
            car_responsiveness=0.90,
            audit_findings_score=0.95,
        )
        rating = service.computeQualityRating("SUP-001")
        assert rating.overall_rating >= 70
        assert rating.is_below_threshold is False

    def test_low_quality_rating(self, service, supplier_profile):
        service.registerSupplier(supplier_profile)
        service.updateRatingMetrics(
            "SUP-001",
            on_time_delivery_rate=0.3,
            first_pass_yield=0.4,
            defect_rate=0.5,
            car_responsiveness=0.2,
            audit_findings_score=0.3,
        )
        rating = service.computeQualityRating("SUP-001")
        assert rating.is_below_threshold is True

    def test_update_rating_metrics(self, service, supplier_profile):
        service.registerSupplier(supplier_profile)
        rating = service.updateRatingMetrics("SUP-001", on_time_delivery_rate=0.9)
        assert rating.on_time_delivery_rate == 0.9


class TestSuspension:

    def test_suspend_supplier(self, service, supplier_profile):
        service.registerSupplier(supplier_profile)
        result = service.suspendSupplier("SUP-001", "Quality issues")
        assert isinstance(result, SuspensionResult)
        assert result.reason == "Quality issues"
        assert "PART-A" in result.affected_parts
        supplier = service.getSupplier("SUP-001")
        assert supplier.status == SupplierStatus.SUSPENDED

    def test_suspend_nonexistent_raises(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.suspendSupplier("FAKE-SUP", "reason")


class TestSupplyChainImpact:

    def test_assess_impact(self, service, supplier_profile):
        service.registerSupplier(supplier_profile)
        result = service.assessSupplyChainImpact("SUP-001")
        assert isinstance(result, SupplyChainImpactReport)
        assert result.affected_parts_count == 2