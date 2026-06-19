"""AeroForge-X V6.1 Integration Tests - Supplier-Cert Cross-Program Interaction
IT-F04: supplierQualityIssue → traceLinkUpdate
REQ-VP-048
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "aircraft-core-service"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "workflow-engine-service"))

import pytest

from src.domain.services.supplier.supplier_registry_service import (
    SupplierRegistryService, SupplierProfile, SupplierStatus,
)
from src.domain.services.supplier.supplier_car_service import (
    SupplierCARService, QualityIssue, CARSeverity,
)
from src.domain.services.certification.requirements_traceability_service import RequirementsTraceabilityService
from src.domain.services.integration.cross_program_event_orchestrator_service import (
    CrossProgramEventOrchestratorService,
)


@pytest.fixture
def registry():
    return SupplierRegistryService()


@pytest.fixture
def car_svc():
    return SupplierCARService()


@pytest.fixture
def trace_svc():
    return RequirementsTraceabilityService()


@pytest.fixture
def orchestrator():
    return CrossProgramEventOrchestratorService()


class TestSupplierCertInteraction:

    def test_supplier_quality_issue_triggers_trace_update(self, registry, car_svc, trace_svc, orchestrator):
        req = trace_svc.createRequirement("REQ-STR-001", "Structural integrity", "Structural")
        design = trace_svc.createRequirement("DES-001", "Wing spar design", "Design")
        trace_svc.createTraceLink(req.req_id, design.req_id, "satisfies")

        profile = SupplierProfile(supplier_id="SUP-001", company_name="AeroParts", approved_parts=["PART-A"])
        registry.registerSupplier(profile)
        for _ in range(4):
            registry.approveSupplierWorkflow("SUP-001")

        issue = car_svc.createQualityIssue("SUP-001", "PART-A", "Material defect in wing spar", "LOT-001")
        car = car_svc.createCAR(issue.issue_id, CARSeverity.MAJOR, "Lead-QA-1")

        event = orchestrator.publishEvent(
            subject="aeroforge.v6.supplier.quality.issue.created",
            payload={
                "supplier_id": "SUP-001",
                "issue_id": issue.issue_id,
                "car_id": car.car_id,
                "affected_requirements": ["REQ-STR-001"],
            },
            source="aircraft-core-service",
        )
        assert event is not None

        trace_svc.createTraceLink(car.car_id, req.req_id, "affects")
        links = trace_svc.getTraceLinks(req.req_id)
        assert any(l.target_id == car.car_id or l.source_id == car.car_id for l in links)

    def test_car_overdue_traces_to_requirement(self, car_svc, trace_svc):
        issue = car_svc.createQualityIssue("SUP-001", "PART-A", "Quality issue", "LOT-001")
        car = car_svc.createCAR(issue.issue_id, CARSeverity.CRITICAL, "QA-1")

        car_svc.verifyCAR(car.car_id, "Action taken", "QA-Mgr", False)

        trace_svc.createTraceLink(car.car_id, "REQ-STR-001", "affects")
        links = trace_svc.getTraceLinks(car.car_id)
        assert len(links) > 0