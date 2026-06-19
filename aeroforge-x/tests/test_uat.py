import pytest

from services.design_center.src.domain.entities.aircraft_spec import AircraftSpec
from services.design_center.src.domain.services.spec_domain_service import SpecDomainService
from services.design_center.src.domain.services.parameter_validator import ValidationEngine
from services.design_center.src.domain.services.aircraft_type_config import AircraftTypeConfig
from services.design_center.src.domain.services.model_domain_service import ParametricModelGenerator
from services.design_center.src.domain.services.design_rule_engine import DesignRuleEngine
from services.bom_center.src.domain.services.ebom_engine import EBOMEngine
from services.mes_center.src.domain.entities.mes_entities import Station, WorkOrder
from services.mes_center.src.domain.services.mes_domain_service import WorkOrderDomainService
from services.qms_service.src.domain.services.qms_domain_service import QmsDomainService
from services.qms_service.src.domain.entities.qms_entities import InspectionRecord


class TestUATScenario1_DesignToEBOM:
    def test_user_inputs_requirements_and_gets_ebom(self) -> None:
        spec = AircraftSpec(
            payload_kg=500, range_km=1000, cruise_speed_kmh=250,
            takeoff_distance_m=100, power_type="electric", created_by="chief-1",
        )

        spec_service = SpecDomainService()
        doc = spec_service.generate_spec_document(spec)
        assert doc["aircraft_type"] == "fixed_wing"
        assert "payload_range_product" in doc["derived_constraints"]

        spec.confirm()
        assert spec.status == "confirmed"

        type_config = AircraftTypeConfig()
        rec = type_config.recommend({"payload_kg": 500, "range_km": 1000, "cruise_speed_kmh": 250, "power_type": "electric"})
        assert rec["recommended_type"] == "fixed_wing"

        template = type_config.get_template("fixed_wing")
        model_gen = ParametricModelGenerator()
        model = model_gen.generate({
            "aircraft_type": "fixed_wing", "payload_kg": 500, "range_km": 1000,
            "cruise_speed_kmh": 250, "template": template,
        })
        assert "assembly" in model

        ebom_engine = EBOMEngine()
        ebom = ebom_engine.generate_from_model(spec.id, model)
        assert ebom.root_item is not None
        assert len(ebom.root_item.children) >= 1


class TestUATScenario2_WorkOrderWithIQC:
    def test_work_order_flow_with_iqc_gate(self) -> None:
        wo_service = WorkOrderDomainService()
        order = wo_service.create_work_order("AAF-001", 1, "normal", None, "prod-1")

        station = Station(name="总装工位", equipment="装配夹具")

        qms_service = QmsDomainService()
        plan = qms_service.generate_iqc_plan("AAF-SPAR-001")
        record = qms_service.record_inspection_result(
            "iqc", "AAF-SPAR-001", "张工", {"dim": 10.0}, {"dim": 10.0}, plan_id=plan.id,
        )
        assert record.is_pass()

        wo_service.dispatch_work_order(order, station, material_available=True)
        order.start()
        order.complete()
        assert order.status == "completed"

        fqc_plan = qms_service.generate_fqc_plan("AAF-001")
        fqc_record = qms_service.record_inspection_result(
            "fqc", "AAF-001", "李工", {"dim": 10.0}, {"dim": 10.0}, plan_id=fqc_plan.id,
        )
        assert fqc_record.is_pass()


class TestUATScenario3_Traceability:
    def test_serial_number_full_trace(self) -> None:
        from services.mes_center.src.domain.services.mes_domain_service import SerialNumberDomainService
        sn_service = SerialNumberDomainService()
        sn = sn_service.assign_serial_number("AAF-SPAR-001", "B2026-001", "CF-Tech")
        assert sn.serial_number.startswith("SN-")

        sn_service.link_to_work_order(sn, "wo-1")
        sn.install(installer="王工")
        assert sn.status == "installed"

        sn_service.update_flight_hours(sn, 100.0)
        assert sn.flight_hours == 100.0


class TestUATScenario4_ParameterValidation:
    def test_invalid_parameters_rejected(self) -> None:
        engine = ValidationEngine()
        violations = engine.validate({
            "payload_kg": 120, "range_km": 200,
            "cruise_speed_kmh": 5000, "takeoff_distance_m": 80, "power_type": "electric",
        })
        assert any(v.parameter == "cruise_speed_kmh" for v in violations)

    def test_electric_high_speed_inconsistency(self) -> None:
        engine = ValidationEngine()
        violations = engine.validate({
            "payload_kg": 120, "range_km": 200,
            "cruise_speed_kmh": 500, "takeoff_distance_m": 80, "power_type": "electric",
        })
        assert any(v.parameter == "cruise_speed_kmh" and v.severity == "error" for v in violations)


class TestUATScenario5_IQCBlocksProduction:
    def test_iqc_fail_blocks_material(self) -> None:
        qms_service = QmsDomainService()
        record = qms_service.record_inspection_result(
            "iqc", "AAF-SPAR-001", "张工",
            {"dimension": 15.0}, {"dimension": 10.0},
        )
        assert not qms_service.is_material_released(record)

        wo_service = WorkOrderDomainService()
        order = wo_service.create_work_order("AAF-001", 1, "normal", None, "prod-1")
        station = Station(name="Test")
        with pytest.raises(ValueError, match="IQC"):
            wo_service.dispatch_work_order(order, station, material_available=False)


class TestUATScenario6_CAPAFlow:
    def test_inspection_fail_triggers_capa(self) -> None:
        qms_service = QmsDomainService()
        record = qms_service.record_inspection_result(
            "iqc", "AAF-001", "张工", {"dim": 15.0}, {"dim": 10.0},
        )
        assert record.result == "fail"

        capa = qms_service.create_capa(record.id, "quality_eng")
        qms_service.execute_capa(capa, "供应商批次问题", "更换供应商", "加强来料检验")
        qms_service.verify_capa(capa, "pass")
        assert capa.status == "closed"


class TestUATScenario7_SpecStatusTransition:
    def test_spec_cannot_skip_confirm(self) -> None:
        spec = AircraftSpec(payload_kg=120, range_km=200, cruise_speed_kmh=120, takeoff_distance_m=80, created_by="chief-1")
        with pytest.raises(ValueError):
            spec.freeze()

    def test_spec_cannot_update_when_confirmed(self) -> None:
        spec = AircraftSpec(payload_kg=120, range_km=200, cruise_speed_kmh=120, takeoff_distance_m=80, created_by="chief-1")
        spec.confirm()
        with pytest.raises(ValueError, match="Cannot update"):
            spec.update_parameters(payload_kg=200)


class TestUATScenario8_DesignRuleValidation:
    def test_design_rule_violation_detected(self) -> None:
        engine = DesignRuleEngine()
        violations = engine.validate({"aspect_ratio": 30, "wing_sweep_deg": 3, "taper_ratio": 0.5})
        assert any(v["rule_id"] == "AERO-001" for v in violations)


class TestUATScenario9_EvtolRecommendation:
    def test_evtol_type_recommended(self) -> None:
        type_config = AircraftTypeConfig()
        result = type_config.recommend({"power_type": "electric", "cruise_speed_kmh": 120, "payload_kg": 200, "vtol": True})
        assert result["recommended_type"] == "evtol"