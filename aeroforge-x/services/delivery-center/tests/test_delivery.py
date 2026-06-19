from __future__ import annotations

import pytest

from src.domain.entities.delivery_entities import (
    DeliveryDocument,
    DeliveryPackage,
    FlightCondition,
    FlightTestPlan,
    SafetyBoundary,
    TestDataRequirement,
    TestPoint,
    TestSubject,
    TestCategory,
    TestPointStatus,
)
from src.domain.services.delivery_package_service import DeliveryPackageService
from src.domain.services.flight_test_plan_service import FlightTestPlanService


class TestFlightTestPlanEntity:
    def test_create_plan(self):
        plan = FlightTestPlan("t1", "p1", "AF-X100", "FAR-23")
        assert plan.tenant_id == "t1"
        assert plan.certification_standard == "FAR-23"

    def test_add_subject(self):
        plan = FlightTestPlan("t1", "p1", "AF-X100", "FAR-23")
        subject = TestSubject("S1", TestCategory.PERFORMANCE, "Test", "Method")
        plan.add_subject(subject)
        assert len(plan.subjects) == 1

    def test_calculate_coverage(self):
        plan = FlightTestPlan("t1", "p1", "AF-X100", "FAR-23")
        subject = TestSubject(
            "S1", TestCategory.PERFORMANCE, "Test", "Method",
            certification_clauses=["23.107", "23.111"],
        )
        plan.add_subject(subject)
        result = plan.calculate_coverage(["23.107", "23.111", "23.125"])
        assert result["covered"] == 2
        assert result["uncovered"] == 1
        assert "23.125" in result["uncovered_clauses"]


class TestFlightTestPlanService:
    def setup_method(self):
        self.service = FlightTestPlanService()

    def test_generate_plan(self):
        plan = self.service.generate_flight_test_plan(
            tenant_id="t1",
            project_id="p1",
            aircraft_model="AF-X100",
            certification_standard="FAR-23",
            design_parameters={"safety_factor": 2.0, "cruise_speed_ktas": 150},
        )
        assert len(plan.subjects) >= 4
        assert plan.total_flights > 0
        assert plan.coverage_percentage > 0

    def test_validate_coverage(self):
        plan = self.service.generate_flight_test_plan("t1", "p1", "AF-X100", "FAR-23")
        result = self.service.validate_coverage(plan.id)
        assert "coverage_percentage" in result
        assert "uncovered_clauses" in result

    def test_optimize_sequence(self):
        plan = self.service.generate_flight_test_plan("t1", "p1", "AF-X100", "FAR-23")
        result = self.service.optimize_test_sequence(plan.id)
        assert "total_flights" in result
        assert "sequence" in result
        assert len(result["sequence"]) > 0

    def test_map_certification_requirements(self):
        result = self.service.map_certification_requirements("FAR-23")
        assert result["total_clauses"] > 0
        assert result["mapped_clauses"] > 0
        assert "mapping" in result

    def test_far25_plan(self):
        plan = self.service.generate_flight_test_plan("t1", "p1", "AF-X200", "FAR-25")
        assert len(plan.subjects) >= 4

    def test_ccar23_plan(self):
        plan = self.service.generate_flight_test_plan("t1", "p1", "AF-X300", "CCAR-23")
        assert len(plan.subjects) >= 4


class TestDeliveryPackageEntity:
    def test_create_package(self):
        pkg = DeliveryPackage("t1", "p1", "AF-X100")
        assert pkg.tenant_id == "t1"
        assert pkg.status == "draft"

    def test_add_document(self):
        pkg = DeliveryPackage("t1", "p1", "AF-X100")
        doc = DeliveryDocument("d1", "aircraft_spec", "Aircraft Spec", "1.0", status="approved")
        pkg.add_document(doc)
        assert len(pkg.documents) == 1

    def test_validate_completeness(self):
        pkg = DeliveryPackage("t1", "p1", "AF-X100")
        doc = DeliveryDocument("d1", "aircraft_spec", "Aircraft Spec", "1.0", status="approved")
        pkg.add_document(doc)
        result = pkg.validate_completeness(["aircraft_spec", "ebom"])
        assert result["completeness_score"] == 50.0
        assert not result["is_complete"]

    def test_generate_index(self):
        pkg = DeliveryPackage("t1", "p1", "AF-X100")
        doc = DeliveryDocument("d1", "aircraft_spec", "Aircraft Spec", "1.0", status="approved",
                               signatures=[{"signer": "eng", "status": "signed"}])
        pkg.add_document(doc)
        index = pkg.generate_index()
        assert index["total_documents"] == 1
        assert len(index["signature_tracking"]) == 1


class TestDeliveryPackageService:
    def setup_method(self):
        self.service = DeliveryPackageService()

    def test_generate_full_package(self):
        docs = [
            {"doc_id": "d1", "doc_type": "aircraft_spec", "name": "Aircraft Spec", "version": "1.0", "status": "approved"},
            {"doc_id": "d2", "doc_type": "ebom", "name": "eBOM", "version": "2.0", "status": "approved"},
            {"doc_id": "d3", "doc_type": "compliance_report", "name": "Compliance Report", "version": "1.0", "status": "approved"},
            {"doc_id": "d4", "doc_type": "airworthiness_checklist", "name": "Airworthiness Checklist", "version": "1.0", "status": "approved"},
        ]
        pkg = self.service.generate_delivery_package("t1", "p1", "AF-X100", docs, "minimal")
        assert len(pkg.documents) == 4
        assert pkg.status == "generated"

    def test_validate_completeness(self):
        docs = [
            {"doc_id": "d1", "doc_type": "aircraft_spec", "name": "Spec", "version": "1.0", "status": "approved"},
        ]
        pkg = self.service.generate_delivery_package("t1", "p1", "AF-X100", docs, "full")
        result = self.service.validate_completeness(pkg.id)
        assert result["completeness_score"] < 100

    def test_generate_package_index(self):
        docs = [
            {"doc_id": "d1", "doc_type": "aircraft_spec", "name": "Spec", "version": "1.0", "status": "approved"},
        ]
        pkg = self.service.generate_delivery_package("t1", "p1", "AF-X100", docs)
        index = self.service.generate_package_index(pkg.id)
        assert index["total_documents"] == 1