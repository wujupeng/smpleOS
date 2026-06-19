import pytest

from services.supply_chain.src.domain.entities.supplier import (
    Supplier, SupplierCategory, QualificationStatus,
    ContactInfo, PerformanceMetrics, Certification,
)
from services.supply_chain.src.domain.services.supplier_domain_service import SupplierDomainService


class TestSupplierEntity:
    def test_create_supplier(self) -> None:
        supplier = Supplier(name="Test Supplier", code="SUP-001")
        assert supplier.qualification_status == QualificationStatus.CONDITIONAL
        assert supplier.id != ""

    def test_qualify_supplier(self) -> None:
        supplier = Supplier(name="Test", code="SUP-001")
        supplier.qualify()
        assert supplier.qualification_status == QualificationStatus.QUALIFIED
        assert supplier.qualification_date != ""
        assert len(supplier.domain_events) == 1

    def test_disqualify_supplier(self) -> None:
        supplier = Supplier(name="Test", code="SUP-001")
        supplier.disqualify("quality issues")
        assert supplier.qualification_status == QualificationStatus.DISQUALIFIED
        assert len(supplier.domain_events) == 1

    def test_update_performance(self) -> None:
        supplier = Supplier(name="Test", code="SUP-001")
        supplier.update_performance(on_time_rate=0.95, quality_rate=0.98, response_days=5.0)
        assert supplier.performance_metrics.on_time_delivery_rate == 0.95
        assert supplier.performance_metrics.quality_pass_rate == 0.98
        assert supplier.performance_metrics.overall_score > 0

    def test_add_certification(self) -> None:
        supplier = Supplier(name="Test", code="SUP-001")
        cert = Certification(name="AS9100", certificate_number="AS9100-001")
        supplier.add_certification(cert)
        assert len(supplier.certifications) == 1
        assert supplier.certifications[0].name == "AS9100"

    def test_supplier_to_dict(self) -> None:
        supplier = Supplier(name="Test", code="SUP-001", tenant_id="t-001",
                            category=SupplierCategory.RAW_MATERIAL)
        d = supplier.to_dict()
        assert d["name"] == "Test"
        assert d["code"] == "SUP-001"
        assert d["category"] == "raw_material"


class TestPerformanceMetrics:
    def test_compute_overall_score(self) -> None:
        metrics = PerformanceMetrics(
            on_time_delivery_rate=0.9,
            quality_pass_rate=0.95,
            avg_response_time_days=5.0,
        )
        score = metrics.compute_overall_score()
        assert score > 0
        assert score <= 1.0
        assert metrics.overall_score == score

    def test_zero_response_time(self) -> None:
        metrics = PerformanceMetrics(
            on_time_delivery_rate=1.0,
            quality_pass_rate=1.0,
            avg_response_time_days=0.0,
        )
        score = metrics.compute_overall_score()
        assert score == 1.0


class TestCertification:
    def test_certification_to_dict(self) -> None:
        cert = Certification(name="ISO9001", certificate_number="ISO-001")
        d = cert.to_dict()
        assert d["name"] == "ISO9001"


class TestSupplierDomainService:
    def test_create_supplier(self) -> None:
        service = SupplierDomainService()
        supplier = service.create_supplier(
            tenant_id="t-001",
            name="Aero Parts Co.",
            code="SUP-001",
            category=SupplierCategory.CUSTOM_PART,
            lead_time_days=14,
            supplied_materials=["AL-6061", "AL-7075"],
        )
        assert supplier.name == "Aero Parts Co."
        assert supplier.code == "SUP-001"
        assert supplier.category == SupplierCategory.CUSTOM_PART
        assert len(supplier.domain_events) == 1

    def test_update_supplier(self) -> None:
        service = SupplierDomainService()
        supplier = service.create_supplier("t-001", "Test", "SUP-001")
        updated = service.update_supplier(
            supplier.id, name="Updated Name", lead_time_days=21,
        )
        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.lead_time_days == 21

    def test_qualify_supplier(self) -> None:
        service = SupplierDomainService()
        supplier = service.create_supplier("t-001", "Test", "SUP-001")
        qualified = service.qualify_supplier(supplier.id)
        assert qualified is not None
        assert qualified.qualification_status == QualificationStatus.QUALIFIED

    def test_disqualify_supplier(self) -> None:
        service = SupplierDomainService()
        supplier = service.create_supplier("t-001", "Test", "SUP-001")
        disqualified = service.disqualify_supplier(supplier.id, "quality issues")
        assert disqualified is not None
        assert disqualified.qualification_status == QualificationStatus.DISQUALIFIED

    def test_evaluate_performance(self) -> None:
        service = SupplierDomainService()
        supplier = service.create_supplier("t-001", "Test", "SUP-001")
        evaluated = service.evaluate_performance(supplier.id, 0.9, 0.95, 3.0)
        assert evaluated is not None
        assert evaluated.performance_metrics.overall_score > 0

    def test_select_supplier_by_material(self) -> None:
        service = SupplierDomainService()
        s1 = service.create_supplier("t-001", "Supplier A", "SUP-A",
                                      category=SupplierCategory.RAW_MATERIAL,
                                      supplied_materials=["AL-6061", "TI-6AL4V"])
        service.qualify_supplier(s1.id)
        service.evaluate_performance(s1.id, 0.95, 0.98, 2.0)

        s2 = service.create_supplier("t-001", "Supplier B", "SUP-B",
                                      category=SupplierCategory.RAW_MATERIAL,
                                      supplied_materials=["AL-6061"])
        service.qualify_supplier(s2.id)
        service.evaluate_performance(s2.id, 0.85, 0.90, 5.0)

        selected = service.select_supplier(material_code="AL-6061")
        assert len(selected) == 2
        assert selected[0].name == "Supplier A"

    def test_select_supplier_by_category_and_score(self) -> None:
        service = SupplierDomainService()
        s1 = service.create_supplier("t-001", "A", "SUP-A", category=SupplierCategory.CUSTOM_PART)
        service.qualify_supplier(s1.id)
        service.evaluate_performance(s1.id, 0.9, 0.95, 3.0)

        s2 = service.create_supplier("t-001", "B", "SUP-B", category=SupplierCategory.RAW_MATERIAL)
        service.qualify_supplier(s2.id)

        selected = service.select_supplier(category=SupplierCategory.CUSTOM_PART, min_score=0.5)
        assert len(selected) == 1
        assert selected[0].name == "A"

    def test_select_supplier_excludes_disqualified(self) -> None:
        service = SupplierDomainService()
        s1 = service.create_supplier("t-001", "A", "SUP-A")
        service.evaluate_performance(s1.id, 0.9, 0.95, 3.0)
        selected = service.select_supplier()
        assert len(selected) == 0

    def test_add_certification(self) -> None:
        service = SupplierDomainService()
        supplier = service.create_supplier("t-001", "Test", "SUP-001")
        cert = Certification(name="AS9100", certificate_number="AS-001")
        updated = service.add_certification(supplier.id, cert)
        assert updated is not None
        assert len(updated.certifications) == 1

    def test_list_suppliers(self) -> None:
        service = SupplierDomainService()
        service.create_supplier("t-001", "A", "SUP-A", category=SupplierCategory.RAW_MATERIAL)
        service.create_supplier("t-001", "B", "SUP-B", category=SupplierCategory.CUSTOM_PART)
        assert len(service.list_suppliers()) == 2
        assert len(service.list_suppliers(category=SupplierCategory.RAW_MATERIAL)) == 1

    def test_get_supplier_not_found(self) -> None:
        service = SupplierDomainService()
        assert service.get_supplier("nonexistent") is None

    def test_update_supplier_not_found(self) -> None:
        service = SupplierDomainService()
        assert service.update_supplier("nonexistent", name="X") is None