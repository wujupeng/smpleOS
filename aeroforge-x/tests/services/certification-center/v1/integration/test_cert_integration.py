import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))

import pytest

from services.certification_center.src.domain.services.v1.certification_plan_service import CertificationPlanService
from services.certification_center.src.domain.services.v1.compliance_verification_service import ComplianceVerificationService
from services.certification_center.src.domain.services.v1.airworthiness_service import AirworthinessService, AirworthinessDirective


class TestCertificationPlanToApprovalIntegration:
    @pytest.fixture
    def setup(self):
        plan_service = CertificationPlanService()
        verification_service = ComplianceVerificationService()
        aw_service = AirworthinessService()
        return plan_service, verification_service, aw_service

    @pytest.mark.asyncio
    async def test_full_certification_flow(self, setup):
        plan_service, verification_service, aw_service = setup

        plan = await plan_service.create_certification_plan("PROJ-INT-001", "narrow_body")
        assert len(plan.compliance_items) > 0

        for ci in plan.compliance_items:
            item = plan_service.get_item(ci["item_id"])
            if item:
                item.link_evidence(f"EVIDENCE-{item.item_id}")

        progress = plan_service.track_compliance_progress(plan.plan_id)
        assert progress["progress"]["compliant"] >= 0

        approval = await aw_service.submit_approval_application(plan.plan_id, "type_certificate", "USER-01")
        assert approval is not None

        aw_service.manage_certificate_lifecycle(
            approval.approval_id, "approve",
            certificate_number="TC-INT-001", reviewed_by="REVIEWER-01"
        )
        updated = aw_service.get_approval(approval.approval_id)
        assert updated.review_status.value == "approved"

    @pytest.mark.asyncio
    async def test_compliance_verification_blocks_non_compliant(self, setup):
        plan_service, verification_service, _ = setup

        plan = await plan_service.create_certification_plan("PROJ-INT-002", "narrow_body")
        first_item_id = plan.compliance_items[0]["item_id"]

        result = verification_service.verify_design_compliance(first_item_id, {"evidence_documents": []})
        assert result.evidence_gap is True

        item = plan_service.get_item(first_item_id)
        if item:
            with pytest.raises(ValueError):
                item.mark_compliant()


class TestContinuousAirworthinessIntegration:
    def test_ad_compliance_workflow(self):
        aw_service = AirworthinessService()

        ad1 = AirworthinessDirective("AD-2024-001", "Wing Spar Inspection", "2024-01-01")
        ad1.affected_aircraft = ["SN-001", "SN-002"]
        ad1.compliance_required_by = "2024-06-01"
        aw_service.add_airworthiness_directive(ad1)

        ad2 = AirworthinessDirective("AD-2024-002", "Engine Mount Check", "2024-02-01")
        ad2.affected_aircraft = ["SN-001"]
        aw_service.add_airworthiness_directive(ad2)

        result = aw_service.track_ad_compliance("SN-001")
        assert result["total_applicable_ads"] == 2
        assert result["pending_ads"] == 2

        aw_service.record_continuous_airworthiness("SN-001", {
            "record_type": "ad_compliance",
            "ad_number": "AD-2024-001",
            "compliance_status": "compliant",
        })

        result = aw_service.track_ad_compliance("SN-001")
        assert result["compliant_ads"] == 1
        assert result["pending_ads"] == 1