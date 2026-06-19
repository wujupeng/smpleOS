from __future__ import annotations

import pytest

from src.domain.services.baseline_domain_service import BaselineDomainService
from src.domain.services.change_mgmt_domain_service import (
    ChangeMgmtDomainService,
    ECRStatus,
    ECOStatus,
)
from src.domain.services.impact_analysis_service import ImpactAnalysisService


class TestBaselineDomainService:
    def setup_method(self):
        self.service = BaselineDomainService()

    def test_establish_baseline(self):
        baseline = self.service.establish_baseline(
            name="Baseline-V1",
            description="First baseline",
            created_by="engineer",
            objects=[
                {"object_id": "OBJ-001", "object_type": "design", "version": "1.0", "name": "Wing"},
                {"object_id": "OBJ-002", "object_type": "design", "version": "1.0", "name": "Fuselage"},
            ],
        )
        assert baseline.name == "Baseline-V1"
        assert len(baseline.objects) == 2
        assert baseline.status == "open"

    def test_freeze_baseline(self):
        baseline = self.service.establish_baseline(
            name="BL-Freeze",
            objects=[{"object_id": "OBJ-001", "object_type": "design", "version": "1.0"}],
        )
        result = self.service.freeze_baseline(baseline.id)
        assert result is not None
        assert result.status == "frozen"
        assert all(o.is_immutable for o in result.objects)

    def test_cannot_add_to_frozen_baseline(self):
        baseline = self.service.establish_baseline(
            name="BL-Frozen",
            objects=[{"object_id": "OBJ-001", "object_type": "design", "version": "1.0"}],
        )
        self.service.freeze_baseline(baseline.id)
        from src.domain.services.baseline_domain_service import BaselineObjectRef
        with pytest.raises(ValueError, match="Cannot add objects to a frozen baseline"):
            baseline.add_object(BaselineObjectRef("OBJ-002", "design", "1.0"))

    def test_unfreeze_baseline(self):
        baseline = self.service.establish_baseline(
            name="BL-Unfreeze",
            objects=[{"object_id": "OBJ-001", "object_type": "design", "version": "1.0"}],
        )
        self.service.freeze_baseline(baseline.id)
        result = self.service.unfreeze_baseline(baseline.id, "manager")
        assert result is not None
        assert result.status == "open"

    def test_check_baseline_integrity(self):
        baseline = self.service.establish_baseline(
            name="BL-Integrity",
            objects=[{"object_id": "OBJ-001", "object_type": "design", "version": "1.0"}],
        )
        result = self.service.check_baseline_integrity(baseline.id)
        assert result["is_intact"] is True
        assert result["total_objects"] == 1

    def test_cannot_freeze_empty_baseline(self):
        baseline = self.service.establish_baseline(name="BL-Empty")
        with pytest.raises(ValueError, match="Cannot freeze empty baseline"):
            baseline.freeze()


class TestChangeMgmtDomainService:
    def setup_method(self):
        self.service = ChangeMgmtDomainService()

    def test_submit_ecr(self):
        ecr = self.service.submit_ecr(
            title="Change wing spar material",
            description="Replace aluminum with CFRP",
            submitter="engineer",
            change_items=[
                {"object_id": "AAF-SPAR-001", "object_type": "structural", "object_name": "翼梁", "current_version": "1.0", "proposed_change": "material: aluminum -> CFRP"},
            ],
        )
        assert ecr.title == "Change wing spar material"
        assert ecr.status == ECRStatus.SUBMITTED
        assert len(ecr.change_items) == 1

    def test_approve_ecr(self):
        ecr = self.service.submit_ecr(title="ECR-Approve", submitter="eng")
        result = self.service.approve_ecr(ecr.id, "manager")
        assert result is not None
        assert result.status == ECRStatus.APPROVED

    def test_reject_ecr(self):
        ecr = self.service.submit_ecr(title="ECR-Reject", submitter="eng")
        result = self.service.reject_ecr(ecr.id, "Not justified")
        assert result is not None
        assert result.status == ECRStatus.REJECTED

    def test_withdraw_ecr(self):
        ecr = self.service.submit_ecr(title="ECR-Withdraw", submitter="eng")
        result = self.service.withdraw_ecr(ecr.id)
        assert result is not None
        assert result.status == ECRStatus.WITHDRAWN

    def test_create_eco_from_approved_ecr(self):
        ecr = self.service.submit_ecr(
            title="ECR-ECO",
            submitter="eng",
            change_items=[{"object_id": "OBJ-001", "object_type": "part", "object_name": "Part", "current_version": "1.0", "proposed_change": "update"}],
        )
        self.service.approve_ecr(ecr.id, "manager")
        eco = self.service.create_eco(ecr.id, "assignee")
        assert eco is not None
        assert eco.ecr_id == ecr.id
        assert eco.status == ECOStatus.PENDING

    def test_cannot_create_eco_from_unapproved_ecr(self):
        ecr = self.service.submit_ecr(title="ECR-NoECO", submitter="eng")
        eco = self.service.create_eco(ecr.id)
        assert eco is None

    def test_execute_change(self):
        ecr = self.service.submit_ecr(
            title="ECR-Exec",
            submitter="eng",
            change_items=[{"object_id": "OBJ-001", "object_type": "part", "object_name": "Part", "current_version": "1.0", "proposed_change": "update"}],
        )
        self.service.approve_ecr(ecr.id, "manager")
        eco = self.service.create_eco(ecr.id, "assignee")
        assert eco is not None

        result = self.service.execute_change(eco.id, "OBJ-001")
        assert result is not None
        assert result.status == ECOStatus.COMPLETED

    def test_generate_ecn(self):
        ecr = self.service.submit_ecr(
            title="ECR-ECN",
            submitter="eng",
            change_items=[{"object_id": "OBJ-001", "object_type": "part", "object_name": "Part", "current_version": "1.0", "proposed_change": "update"}],
        )
        self.service.approve_ecr(ecr.id, "manager")
        eco = self.service.create_eco(ecr.id, "assignee")
        self.service.execute_change(eco.id, "OBJ-001")

        ecn = self.service.generate_ecn(eco.id, "ECN Title", "ECN Description")
        assert ecn is not None
        assert len(ecn.affected_parties) > 0

    def test_full_ecr_eco_ecn_flow(self):
        ecr = self.service.submit_ecr(
            title="Full Flow ECR",
            submitter="engineer",
            change_items=[
                {"object_id": "OBJ-A", "object_type": "structural", "object_name": "翼梁", "current_version": "1.0", "proposed_change": "material change"},
                {"object_id": "OBJ-B", "object_type": "part", "object_name": "肋板", "current_version": "2.0", "proposed_change": "dimension update"},
            ],
        )
        assert ecr.status == ECRStatus.SUBMITTED

        self.service.approve_ecr(ecr.id, "manager")
        assert ecr.status == ECRStatus.APPROVED

        eco = self.service.create_eco(ecr.id, "assignee")
        assert eco.status == ECOStatus.PENDING

        self.service.execute_change(eco.id, "OBJ-A")
        assert eco.status == ECOStatus.IN_PROGRESS

        self.service.execute_change(eco.id, "OBJ-B")
        assert eco.status == ECOStatus.COMPLETED

        ecn = self.service.generate_ecn(eco.id, "Change Notice", "Complete change")
        assert ecn is not None


class TestImpactAnalysisService:
    def setup_method(self):
        self.service = ImpactAnalysisService()
        self.service.register_bom_graph("WING-001", ["SPAR-001", "RIB-001", "SKIN-001"])
        self.service.register_process_link("SPAR-001", ["PROC-SPAR-FAB", "PROC-SPAR-INSPECT"])
        self.service.register_wip_batch("BATCH-001", ["SPAR-001", "RIB-001"])

    def test_analyze_affected_parts(self):
        from src.domain.services.change_mgmt_domain_service import ChangeMgmtDomainService
        change_service = ChangeMgmtDomainService()
        ecr = change_service.submit_ecr(
            title="Change wing",
            submitter="eng",
            change_items=[{"object_id": "WING-001", "object_type": "assembly", "object_name": "机翼", "current_version": "1.0", "proposed_change": "redesign"}],
        )

        result = self.service.analyze_affected_parts(ecr)
        assert len(result) > 0
        direct = [r for r in result if r["change_type"] != "propagated"]
        assert len(direct) >= 1

    def test_analyze_affected_bom(self):
        from src.domain.services.change_mgmt_domain_service import ChangeMgmtDomainService
        change_service = ChangeMgmtDomainService()
        ecr = change_service.submit_ecr(
            title="Change spar",
            submitter="eng",
            change_items=[{"object_id": "SPAR-001", "object_type": "structural", "object_name": "翼梁", "current_version": "1.0", "proposed_change": "material change"}],
        )

        result = self.service.analyze_affected_bom(ecr)
        assert len(result) > 0
        bom_types = {r["bom_type"] for r in result}
        assert "ebom" in bom_types

    def test_safety_critical_detection(self):
        from src.domain.services.change_mgmt_domain_service import ChangeMgmtDomainService
        change_service = ChangeMgmtDomainService()
        ecr = change_service.submit_ecr(
            title="Change spar material",
            submitter="eng",
            change_items=[{"object_id": "AAF-SPAR-001", "object_type": "structural", "object_name": "翼梁", "current_version": "1.0", "proposed_change": "material change"}],
        )

        is_critical = self.service.check_safety_critical(ecr)
        assert is_critical is True

    def test_full_analysis(self):
        from src.domain.services.change_mgmt_domain_service import ChangeMgmtDomainService
        change_service = ChangeMgmtDomainService()
        ecr = change_service.submit_ecr(
            title="Full analysis",
            submitter="eng",
            change_items=[{"object_id": "SPAR-001", "object_type": "structural", "object_name": "翼梁", "current_version": "1.0", "proposed_change": "material: Al -> CFRP"}],
        )

        result = self.service.full_analysis(ecr)
        assert result.impact_level in ("low", "medium", "high", "critical")
        assert result.safety_critical is True
        assert len(result.affected_parts) > 0