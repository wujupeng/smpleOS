import pytest

from services.design_center.src.domain.entities.aircraft_spec import AircraftSpec
from services.design_center.src.domain.services.spec_domain_service import SpecDomainService
from services.design_center.src.domain.services.parameter_validator import ValidationEngine
from services.design_center.src.domain.services.aircraft_type_config import AircraftTypeConfig
from services.design_center.src.domain.services.model_domain_service import ParametricModelGenerator
from services.design_center.src.domain.services.design_rule_engine import DesignRuleEngine
from services.plm_center.src.domain.entities.product_tree import ProductNode, ProductTree
from services.plm_center.src.domain.services.version_domain_service import VersionDomainService
from services.bom_center.src.domain.entities.bom_item import EBOM
from services.bom_center.src.domain.services.ebom_engine import EBOMEngine
from services.mes_center.src.domain.entities.mes_entities import SerialNumber, Station, WorkOrder
from services.mes_center.src.domain.services.mes_domain_service import WorkOrderDomainService, StationDomainService, SerialNumberDomainService
from services.qms_service.src.domain.entities.qms_entities import CAPA, InspectionPlan, InspectionRecord
from services.qms_service.src.domain.services.qms_domain_service import QmsDomainService


class TestE2EDesignToEBOM:
    def test_full_design_to_ebom_flow(self) -> None:
        spec = AircraftSpec(
            aircraft_type="fixed_wing",
            payload_kg=120,
            range_km=200,
            cruise_speed_kmh=120,
            takeoff_distance_m=80,
            power_type="electric",
            created_by="chief-1",
        )

        spec_service = SpecDomainService()
        violations = spec_service.validate_parameters(spec.to_dict())
        assert len(violations) == 0 or all(v["severity"] != "error" for v in violations)

        spec.confirm()
        assert spec.status == "confirmed"
        assert len(spec.domain_events) == 1
        assert spec.domain_events[0].event_type == "aircraft.spec.confirmed"

        type_config = AircraftTypeConfig()
        recommendation = type_config.recommend({
            "payload_kg": 120, "range_km": 200, "cruise_speed_kmh": 120, "power_type": "electric",
        })
        assert recommendation["recommended_type"] in ["fixed_wing", "evtol"]

        template = type_config.get_template(spec.aircraft_type)
        model_gen = ParametricModelGenerator()
        model = model_gen.generate({
            "aircraft_type": spec.aircraft_type,
            "payload_kg": spec.payload_kg,
            "range_km": spec.range_km,
            "cruise_speed_kmh": spec.cruise_speed_kmh,
            "template": template,
        })
        assert "assembly" in model
        assert "fuselage" in model["assembly"]["components"]
        assert "wing" in model["assembly"]["components"]

        rule_engine = DesignRuleEngine()
        rule_violations = rule_engine.validate({
            "aspect_ratio": template["default_params"]["aspect_ratio"],
            "wing_sweep_deg": template["default_params"]["wing_sweep_deg"],
            "taper_ratio": template["default_params"]["taper_ratio"],
        })
        assert len(rule_violations) == 0

        ebom_engine = EBOMEngine()
        ebom = ebom_engine.generate_from_model(spec_id=spec.id, model_data=model)
        assert ebom.root_item is not None
        assert len(ebom.root_item.children) == 3

        ebom.publish()
        assert ebom.status == "published"
        assert len(ebom.domain_events) == 1
        assert ebom.domain_events[0].event_type == "ebom.generated"


class TestE2EWorkOrderToInspection:
    def test_work_order_with_iqc_gate(self) -> None:
        wo_service = WorkOrderDomainService()
        order = wo_service.create_work_order("AAF-001", 2, "normal", None, "prod-1")
        assert order.status == "created"

        station = Station(name="碳纤维铺层工位", equipment="自动铺层机")

        with pytest.raises(ValueError, match="IQC"):
            wo_service.dispatch_work_order(order, station, material_available=False)
        assert order.status == "created"

        qms_service = QmsDomainService()
        plan = qms_service.generate_iqc_plan("AAF-SPAR-001", order.order_code)
        assert plan.inspection_type == "iqc"

        record = qms_service.record_inspection_result(
            "iqc", "AAF-SPAR-001", "张工",
            {"dimension": 10.02, "weight": 2.31},
            {"dimension": 10.0, "weight": 2.3},
            plan_id=plan.id,
        )
        assert record.is_pass()
        assert qms_service.is_material_released(record) is True

        wo_service.dispatch_work_order(order, station, material_available=True)
        assert order.status == "dispatched"

        order.start()
        assert order.status == "in_progress"

        order.complete()
        assert order.status == "completed"

        fqc_plan = qms_service.generate_fqc_plan("AAF-001", order.order_code)
        fqc_record = qms_service.record_inspection_result(
            "fqc", "AAF-001", "李工",
            {"dimension": 10.0}, {"dimension": 10.0},
            plan_id=fqc_plan.id,
        )
        assert fqc_record.is_pass()


class TestE2ETraceability:
    def test_serial_number_traceability(self) -> None:
        sn_service = SerialNumberDomainService()
        sn = sn_service.assign_serial_number("AAF-SPAR-001", "B2026-001", "CF-Tech")
        assert sn.status == "in_stock"
        assert sn.serial_number.startswith("SN-")

        sn_service.link_to_work_order(sn, "wo-1")
        assert sn.status == "in_production"
        assert sn.work_order_id == "wo-1"

        sn.install(installer="王工")
        assert sn.status == "installed"
        assert sn.installer == "王工"

        sn_service.update_flight_hours(sn, 50.0)
        assert sn.flight_hours == 50.0

    def test_product_tree_where_used(self) -> None:
        tree = ProductTree(name="AAF-001", created_by="chief-1")
        root = ProductNode(part_id="aircraft-1", name="飞行器总装", part_type="assembly")
        tree.set_root(root)

        wing = ProductNode(part_id="wing-1", name="机翼组件", quantity=1)
        tree.add_part("aircraft-1", wing)

        spar = ProductNode(part_id="spar-1", name="翼梁", quantity=2)
        wing.add_child(spar)

        used_in = tree.where_used("spar-1")
        assert "wing-1" in used_in or "aircraft-1" in used_in


class TestE2ECAPAFlow:
    def test_inspection_fail_to_capa(self) -> None:
        qms_service = QmsDomainService()

        record = qms_service.record_inspection_result(
            "iqc", "AAF-SPAR-001", "张工",
            {"dimension": 15.0}, {"dimension": 10.0},
        )
        assert record.result == "fail"
        assert not qms_service.is_material_released(record)

        capa = qms_service.create_capa(record.id, "quality_eng")
        assert capa.status == "open"

        qms_service.execute_capa(capa, "供应商批次不合格", "更换供应商", "加强来料检验")
        assert capa.status == "executing"

        qms_service.verify_capa(capa, "pass")
        assert capa.status == "closed"


class TestE2EVersionControl:
    def test_version_create_and_compare(self) -> None:
        version_service = VersionDomainService()

        from services.plm_center.src.domain.services.version_domain_service import Version
        v1 = Version(object_id="obj-1", major=1, minor=0, snapshot={"wingspan": 15, "weight": 300})
        v2 = Version(object_id="obj-1", major=1, minor=1, snapshot={"wingspan": 16, "weight": 300, "range": 250})

        diff = version_service.compare_versions(v1, v2)
        assert "wingspan" in diff["changed"]
        assert "range" in diff["added"]