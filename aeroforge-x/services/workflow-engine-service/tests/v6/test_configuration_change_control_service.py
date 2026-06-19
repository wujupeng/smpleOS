"""AeroForge-X V6.0/V6.1 Unit Tests - ConfigurationChangeControlService
REQ-CFG-018~022, REQ-VP-020
"""

import pytest

from src.domain.services.configuration_management.configuration_change_control_service import (
    ConfigurationChangeControlService,
    ConfigurationChangeRequest,
    ChangeClass,
    ChangeRequestStatus,
    ChangeApproval,
    ImpactAnalysisResult,
    ChangeImplementationResult,
    ChangeVerificationResult,
)


@pytest.fixture
def service():
    return ConfigurationChangeControlService()


@pytest.fixture
def class_i_request():
    return ConfigurationChangeRequest(
        request_id="CR-001",
        block_id="BLK-A320-Block-1",
        change_class=ChangeClass.CLASS_I,
        change_type="DesignChange",
        description="Wing span modification",
        requested_by="engineer-1",
        affected_items=[
            {"item_id": "item-1", "affected_views": ["Design", "Manufacturing"], "affected_sns": ["SN-001"]},
        ],
    )


@pytest.fixture
def class_ii_request():
    return ConfigurationChangeRequest(
        request_id="CR-002",
        block_id="BLK-A320-Block-1",
        change_class=ChangeClass.CLASS_II,
        change_type="ProcessChange",
        description="Process parameter update",
        requested_by="engineer-2",
        affected_items=[
            {"item_id": "item-2", "affected_views": ["Manufacturing"], "affected_sns": []},
        ],
    )


class TestSubmitChangeRequest:

    def test_submit_request(self, service, class_i_request):
        result = service.submitChangeRequest(class_i_request)
        assert result.status == ChangeRequestStatus.SUBMITTED

    def test_submit_duplicate_raises(self, service, class_i_request):
        service.submitChangeRequest(class_i_request)
        with pytest.raises(ValueError, match="already exists"):
            service.submitChangeRequest(class_i_request)

    def test_audit_trail_records_submission(self, service, class_i_request):
        service.submitChangeRequest(class_i_request)
        trail = service.getAuditTrail()
        assert any(e["action"] == "Submitted" for e in trail)


class TestImpactAnalysis:

    def test_perform_impact_analysis(self, service, class_i_request):
        service.submitChangeRequest(class_i_request)
        result = service.performImpactAnalysis("CR-001")
        assert isinstance(result, ImpactAnalysisResult)
        assert "item-1" in result.affected_design_items
        assert "item-1" in result.affected_mfg_items
        assert "SN-001" in result.affected_sns
        assert result.estimated_propagation_time_ms > 0

    def test_impact_analysis_updates_status(self, service, class_i_request):
        service.submitChangeRequest(class_i_request)
        service.performImpactAnalysis("CR-001")
        req = service.getChangeRequest("CR-001")
        assert req.status == ChangeRequestStatus.IMPACT_ANALYZED

    def test_impact_analysis_nonexistent_raises(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.performImpactAnalysis("CR-FAKE")


class TestApproval:

    def test_approve_class_i(self, service, class_i_request):
        service.submitChangeRequest(class_i_request)
        service.performImpactAnalysis("CR-001")
        approval = service.approveChangeRequest("CR-001", "Chief-Engineer", ChangeClass.CLASS_I)
        assert approval.approved is True
        req = service.getChangeRequest("CR-001")
        assert req.status == ChangeRequestStatus.APPROVED

    def test_approve_class_ii(self, service, class_ii_request):
        service.submitChangeRequest(class_ii_request)
        service.performImpactAnalysis("CR-002")
        approval = service.approveChangeRequest("CR-002", "Lead-Engineer", ChangeClass.CLASS_II)
        assert approval.approved is True

    def test_class_i_requires_chief(self, service, class_i_request):
        service.submitChangeRequest(class_i_request)
        service.performImpactAnalysis("CR-001")
        with pytest.raises(ValueError, match="Chief Engineer"):
            service.approveChangeRequest("CR-001", "Lead-Engineer", ChangeClass.CLASS_I)

    def test_class_ii_requires_lead(self, service, class_ii_request):
        service.submitChangeRequest(class_ii_request)
        service.performImpactAnalysis("CR-002")
        with pytest.raises(ValueError, match="Lead Engineer"):
            service.approveChangeRequest("CR-002", "Engineer-1", ChangeClass.CLASS_II)


class TestImplementation:

    def test_implement_approved_change(self, service, class_i_request):
        service.submitChangeRequest(class_i_request)
        service.performImpactAnalysis("CR-001")
        service.approveChangeRequest("CR-001", "Chief-Engineer", ChangeClass.CLASS_I)
        result = service.implementChange("CR-001")
        assert isinstance(result, ChangeImplementationResult)
        assert result.propagation_completed is True
        assert result.items_updated > 0

    def test_implement_without_approval_raises(self, service, class_i_request):
        service.submitChangeRequest(class_i_request)
        with pytest.raises(ValueError, match="approved"):
            service.implementChange("CR-001")


class TestVerification:

    def test_verify_implemented_change(self, service, class_i_request):
        service.submitChangeRequest(class_i_request)
        service.performImpactAnalysis("CR-001")
        service.approveChangeRequest("CR-001", "Chief-Engineer", ChangeClass.CLASS_I)
        service.implementChange("CR-001")
        result = service.verifyChange("CR-001")
        assert isinstance(result, ChangeVerificationResult)
        assert result.is_verified is True
        assert result.baseline_updated is True
        req = service.getChangeRequest("CR-001")
        assert req.status == ChangeRequestStatus.VERIFIED

    def test_verify_without_implementation_raises(self, service, class_i_request):
        service.submitChangeRequest(class_i_request)
        service.performImpactAnalysis("CR-001")
        service.approveChangeRequest("CR-001", "Chief-Engineer", ChangeClass.CLASS_I)
        with pytest.raises(ValueError, match="implemented"):
            service.verifyChange("CR-001")


class TestFullWorkflow:

    def test_complete_change_lifecycle(self, service, class_i_request):
        service.submitChangeRequest(class_i_request)
        service.performImpactAnalysis("CR-001")
        service.approveChangeRequest("CR-001", "Chief-Engineer", ChangeClass.CLASS_I)
        service.implementChange("CR-001")
        result = service.verifyChange("CR-001")
        assert result.is_verified is True
        trail = service.getAuditTrail()
        assert len(trail) == 5