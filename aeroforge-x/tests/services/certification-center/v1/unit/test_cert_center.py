import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', '..'))

import pytest

from services.certification_center.src.domain.entities.v1.certification_plan import CertificationPlan, PlanStatus
from services.certification_center.src.domain.entities.v1.compliance_item import ComplianceItem, ComplianceMethod, ComplianceStatus
from services.certification_center.src.domain.entities.v1.airworthiness_approval import AirworthinessApproval, ReviewStatus
from services.certification_center.src.domain.services.v1.certification_plan_service import CertificationPlanService
from services.certification_center.src.domain.services.v1.compliance_verification_service import ComplianceVerificationService
from services.certification_center.src.domain.services.v1.airworthiness_service import AirworthinessService, AirworthinessDirective, ServiceBulletin


class TestCertificationPlan:
    def test_create_plan(self):
        plan = CertificationPlan(project_id="PROJ-001", aircraft_type="narrow_body")
        assert plan.project_id == "PROJ-001"
        assert plan.status == PlanStatus.DRAFT

    def test_add_compliance_item(self):
        plan = CertificationPlan(project_id="PROJ-001", aircraft_type="narrow_body")
        plan.add_compliance_item({"item_id": "CI-001", "regulation_clause": "25.301", "status": "open"})
        assert len(plan.compliance_items) == 1

    def test_get_progress(self):
        plan = CertificationPlan(project_id="PROJ-001", aircraft_type="narrow_body")
        plan.add_compliance_item({"status": "compliant"})
        plan.add_compliance_item({"status": "open"})
        progress = plan.get_progress()
        assert progress["total"] == 2
        assert progress["compliant"] == 1
        assert progress["progress_percentage"] == 50.0


class TestComplianceItem:
    def test_create_item(self):
        item = ComplianceItem(plan_id="PLAN-001", regulation_clause="25.301", clause_title="Loads - General")
        assert item.status == ComplianceStatus.OPEN
        assert item.evidence_gap is True

    def test_assign_method(self):
        item = ComplianceItem(plan_id="PLAN-001", regulation_clause="25.301", clause_title="Loads")
        item.assign_compliance_method(ComplianceMethod.MOC1)
        assert item.compliance_method == ComplianceMethod.MOC1

    def test_link_evidence(self):
        item = ComplianceItem(plan_id="PLAN-001", regulation_clause="25.301", clause_title="Loads")
        item.link_evidence("RPT-001")
        assert len(item.evidence_refs) == 1
        assert item.evidence_gap is False
        assert item.status == ComplianceStatus.IN_PROGRESS

    def test_mark_compliant(self):
        item = ComplianceItem(plan_id="PLAN-001", regulation_clause="25.301", clause_title="Loads")
        item.link_evidence("RPT-001")
        item.mark_compliant()
        assert item.status == ComplianceStatus.COMPLIANT

    def test_mark_compliant_blocked_by_gap(self):
        item = ComplianceItem(plan_id="PLAN-001", regulation_clause="25.301", clause_title="Loads")
        with pytest.raises(ValueError, match="evidence gap"):
            item.mark_compliant()


class TestAirworthinessApproval:
    def test_create_approval(self):
        approval = AirworthinessApproval("PLAN-001", "type_certificate")
        assert approval.review_status == ReviewStatus.SUBMITTED

    def test_approve(self):
        approval = AirworthinessApproval("PLAN-001", "type_certificate")
        approval.approve("TC-2024-001", reviewed_by="REVIEWER-01")
        assert approval.review_status == ReviewStatus.APPROVED
        assert approval.certificate_number == "TC-2024-001"

    def test_conditionally_approve(self):
        approval = AirworthinessApproval("PLAN-001", "type_certificate")
        approval.conditionally_approve(["Complete flight test"], "TC-2024-002", "REVIEWER-01")
        assert approval.review_status == ReviewStatus.CONDITIONALLY_APPROVED
        assert len(approval.conditions) == 1

    def test_reject(self):
        approval = AirworthinessApproval("PLAN-001", "type_certificate")
        approval.reject("Insufficient evidence", "REVIEWER-01")
        assert approval.review_status == ReviewStatus.REJECTED

    def test_add_finding(self):
        approval = AirworthinessApproval("PLAN-001", "type_certificate")
        approval.review_status = ReviewStatus.UNDER_REVIEW
        approval.add_finding({"type": "minor", "description": "Documentation incomplete"})
        assert len(approval.review_findings) == 1
        assert approval.review_status == ReviewStatus.FINDINGS_ISSUED


class TestCertificationPlanService:
    @pytest.fixture
    def service(self):
        return CertificationPlanService()

    @pytest.mark.asyncio
    async def test_create_plan_with_compliance_items(self, service):
        plan = await service.create_certification_plan("PROJ-001", "narrow_body")
        assert len(plan.compliance_items) > 0
        assert plan.certification_standard == "FAR-25"

    @pytest.mark.asyncio
    async def test_track_progress(self, service):
        plan = await service.create_certification_plan("PROJ-001", "narrow_body")
        progress = service.track_compliance_progress(plan.plan_id)
        assert progress["total"] > 0

    @pytest.mark.asyncio
    async def test_assign_method(self, service):
        plan = await service.create_certification_plan("PROJ-001", "narrow_body")
        item_id = plan.compliance_items[0]["item_id"]
        item = service.assign_compliance_method(item_id, ComplianceMethod.MOC3)
        assert item.compliance_method == ComplianceMethod.MOC3


class TestComplianceVerificationService:
    @pytest.fixture
    def service(self):
        return ComplianceVerificationService()

    def test_verify_design_compliant(self, service):
        result = service.verify_design_compliance("CI-001", {
            "evidence_documents": ["design_report_v1.pdf", "analysis_results.xlsx"],
            "design_rules_passed": True,
            "cae_results_acceptable": True,
        })
        assert result.is_compliant is True
        assert result.result == "compliant"

    def test_verify_design_evidence_gap(self, service):
        result = service.verify_design_compliance("CI-002", {"evidence_documents": []})
        assert result.evidence_gap is True
        assert result.result == "evidence_gap"

    def test_verify_design_non_compliant(self, service):
        result = service.verify_design_compliance("CI-003", {
            "evidence_documents": ["design_report.pdf", "analysis.xlsx"],
            "design_rules_passed": False,
        })
        assert result.is_compliant is False

    def test_verify_manufacturing_compliant(self, service):
        result = service.verify_manufacturing_compliance("CI-004", {
            "evidence_documents": ["process_qualification.pdf", "ndt_results.pdf"],
            "dimensions_in_tolerance": True,
            "ndt_passed": True,
        })
        assert result.is_compliant is True

    def test_verify_test_compliant(self, service):
        result = service.verify_test_compliance("CI-005", {
            "evidence_documents": ["test_report.pdf", "test_data.csv"],
            "test_passed": True,
            "within_flight_envelope": True,
        })
        assert result.is_compliant is True

    def test_link_evidence(self, service):
        item = ComplianceItem("PLAN-001", "25.301", "Loads")
        result = service.link_evidence("CI-001", "RPT-001", item)
        assert result["linked"] is True
        assert item.evidence_gap is False


class TestAirworthinessService:
    @pytest.fixture
    def service(self):
        return AirworthinessService()

    @pytest.mark.asyncio
    async def test_submit_approval(self, service):
        approval = await service.submit_approval_application("PLAN-001", "type_certificate", "USER-01")
        assert approval.review_status == ReviewStatus.SUBMITTED

    def test_track_review_progress(self, service):
        import asyncio
        approval = asyncio.get_event_loop().run_until_complete(
            service.submit_approval_application("PLAN-001", "type_certificate")
        )
        progress = service.track_review_progress(approval.approval_id)
        assert progress["review_status"] == "submitted"

    def test_manage_certificate_lifecycle(self, service):
        import asyncio
        approval = asyncio.get_event_loop().run_until_complete(
            service.submit_approval_application("PLAN-001", "type_certificate")
        )
        result = service.manage_certificate_lifecycle(
            approval.approval_id, "approve",
            certificate_number="TC-2024-001", reviewed_by="REVIEWER-01"
        )
        assert result["new_status"] == "approved"

    def test_ad_compliance_tracking(self, service):
        ad = AirworthinessDirective("AD-2024-001", "Wing Spar Inspection", "2024-01-01")
        ad.affected_aircraft = ["SN-001", "SN-002"]
        service.add_airworthiness_directive(ad)
        result = service.track_ad_compliance("SN-001")
        assert result["total_applicable_ads"] == 1
        assert result["pending_ads"] == 1

    def test_sb_compliance_tracking(self, service):
        sb = ServiceBulletin("SB-2024-001", "Hydraulic System Update", "OEM", "2024-03-01")
        sb.affected_aircraft = ["SN-001"]
        service.add_service_bulletin(sb)
        result = service.track_sb_compliance("SN-001")
        assert result["total_applicable_sbs"] == 1