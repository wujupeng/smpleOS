from __future__ import annotations

import pytest

from src.domain.entities.compliance import (
    CheckCategory,
    CheckSeverity,
    ComplianceCheck,
    ComplianceCheckResult,
    ComplianceRequirement,
    ComplianceStandard,
    ComplianceStatus,
)
from src.domain.services.compliance_domain_service import ComplianceDomainService


class TestComplianceEntities:
    def test_compliance_requirement(self):
        req = ComplianceRequirement(
            requirement_id="FAR23-001",
            standard=ComplianceStandard.FAR_23,
            clause="23.21",
            description="Proof of compliance",
            category=CheckCategory.DESIGN,
            severity=CheckSeverity.CRITICAL,
        )
        data = req.to_dict()
        assert data["requirement_id"] == "FAR23-001"
        assert data["standard"] == "FAR-23"
        assert data["severity"] == "critical"

    def test_compliance_check_result(self):
        result = ComplianceCheckResult(
            requirement_id="FAR23-001",
            status=ComplianceStatus.COMPLIANT,
            evidence="Safety factor 2.0 meets requirement",
        )
        data = result.to_dict()
        assert data["status"] == "compliant"
        assert data["evidence"] == "Safety factor 2.0 meets requirement"

    def test_compliance_check_aggregate(self):
        check = ComplianceCheck(
            tenant_id="t1",
            project_id="p1",
            aircraft_model="AF-X100",
            standards=[ComplianceStandard.FAR_23],
        )
        assert check.overall_status == ComplianceStatus.NOT_ASSESSED

        result = ComplianceCheckResult(
            requirement_id="FAR23-001",
            status=ComplianceStatus.COMPLIANT,
        )
        check.add_result(result)
        assert check.overall_status == ComplianceStatus.COMPLIANT

    def test_compliance_check_non_compliant(self):
        check = ComplianceCheck(
            tenant_id="t1",
            project_id="p1",
            aircraft_model="AF-X100",
            standards=[ComplianceStandard.FAR_23],
        )
        result = ComplianceCheckResult(
            requirement_id="FAR23-001",
            status=ComplianceStatus.NON_COMPLIANT,
            findings=["Safety factor too low"],
        )
        check.add_result(result)
        assert check.overall_status == ComplianceStatus.NON_COMPLIANT

    def test_compliance_check_summary(self):
        check = ComplianceCheck(
            tenant_id="t1",
            project_id="p1",
            aircraft_model="AF-X100",
            standards=[ComplianceStandard.FAR_23],
        )
        check.add_result(ComplianceCheckResult("R1", ComplianceStatus.COMPLIANT))
        check.add_result(ComplianceCheckResult("R2", ComplianceStatus.NON_COMPLIANT))
        check.add_result(ComplianceCheckResult("R3", ComplianceStatus.COMPLIANT))

        summary = check.get_summary()
        assert summary["total_requirements"] == 3
        assert summary["status_counts"]["compliant"] == 2
        assert summary["status_counts"]["non_compliant"] == 1


class TestComplianceDomainService:
    def setup_method(self):
        self.service = ComplianceDomainService()

    def test_design_compliance_compliant(self):
        check = self.service.check_design_compliance(
            tenant_id="t1",
            project_id="p1",
            aircraft_model="AF-X100",
            standards=[ComplianceStandard.FAR_23],
            design_parameters={
                "safety_factor": 2.0,
                "max_stress_mpa": 200,
                "yield_stress_mpa": 400,
                "materials_certified": True,
                "system_redundancy": "dual",
            },
        )
        assert check.overall_status == ComplianceStatus.COMPLIANT
        assert len(check.results) > 0

    def test_design_compliance_non_compliant(self):
        check = self.service.check_design_compliance(
            tenant_id="t1",
            project_id="p1",
            aircraft_model="AF-X100",
            standards=[ComplianceStandard.FAR_23],
            design_parameters={
                "safety_factor": 1.0,
                "max_stress_mpa": 500,
                "yield_stress_mpa": 400,
                "materials_certified": False,
                "system_redundancy": "single",
            },
        )
        assert check.overall_status == ComplianceStatus.NON_COMPLIANT

    def test_manufacturing_compliance(self):
        check = self.service.check_manufacturing_compliance(
            tenant_id="t1",
            project_id="p1",
            aircraft_model="AF-X100",
            standards=[ComplianceStandard.FAR_23],
            manufacturing_data={
                "processes_qualified": True,
                "ndt_coverage_percent": 100,
                "all_inspections_complete": True,
                "first_article_inspected": True,
                "material_traceability": True,
                "trace_chain_complete": True,
                "batch_records_complete": True,
            },
        )
        assert check.overall_status == ComplianceStatus.COMPLIANT

    def test_manufacturing_non_compliant(self):
        check = self.service.check_manufacturing_compliance(
            tenant_id="t1",
            project_id="p1",
            aircraft_model="AF-X100",
            standards=[ComplianceStandard.FAR_23],
            manufacturing_data={
                "processes_qualified": False,
                "ndt_coverage_percent": 80,
                "all_inspections_complete": False,
                "first_article_inspected": False,
                "material_traceability": False,
                "trace_chain_complete": False,
                "batch_records_complete": True,
            },
        )
        assert check.overall_status == ComplianceStatus.NON_COMPLIANT

    def test_generate_compliance_report(self):
        design_check = self.service.check_design_compliance(
            tenant_id="t1",
            project_id="p1",
            aircraft_model="AF-X100",
            standards=[ComplianceStandard.FAR_23],
            design_parameters={"safety_factor": 2.0, "materials_certified": True},
        )

        report = self.service.generate_compliance_report(
            tenant_id="t1",
            project_id="p1",
            aircraft_model="AF-X100",
            standards=[ComplianceStandard.FAR_23],
            design_check_id=design_check.id,
        )
        assert report.report_id is not None
        assert report.overall_status in (ComplianceStatus.COMPLIANT, ComplianceStatus.PARTIALLY_COMPLIANT)

    def test_get_requirements(self):
        reqs = self.service.get_requirements(ComplianceStandard.FAR_23)
        assert len(reqs) > 0
        assert all(r.standard == ComplianceStandard.FAR_23 for r in reqs)

    def test_far25_requirements(self):
        reqs = self.service.get_requirements(ComplianceStandard.FAR_25)
        assert len(reqs) > 0
        assert any(r.clause == "25.571" for r in reqs)

    def test_ccar23_requirements(self):
        reqs = self.service.get_requirements(ComplianceStandard.CCAR_23)
        assert len(reqs) > 0

    def test_list_checks(self):
        self.service.check_design_compliance("t1", "p1", "AF-X100", [ComplianceStandard.FAR_23], {})
        self.service.check_design_compliance("t1", "p2", "AF-X200", [ComplianceStandard.FAR_25], {})

        checks = self.service.list_checks("t1")
        assert len(checks) == 2

        checks_p1 = self.service.list_checks("t1", "p1")
        assert len(checks_p1) == 1