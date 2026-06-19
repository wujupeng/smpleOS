import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'services', 'design-center'))

import unittest
from decimal import Decimal

from src.domain.entities.v1.parametric_model import ParametricModel, ModelType, ModelStatus
from src.domain.entities.v1.airframe_model import AirframeModel, FuselageParams, WingParams, TailParams
from src.domain.entities.v1.structure_model import StructureModel, StructureComponentType
from src.domain.entities.v1.powertrain_model import PowertrainModel, MotorSpec, BatterySpec
from src.domain.entities.v1.wire_harness_model import WireHarnessModel, WireSpec, ConnectorSpec, HarnessType
from src.domain.entities.v1.design_rule import DesignRule, RuleType, RuleSeverity, BUILTIN_DESIGN_RULES
from src.domain.services.v1.param_model_service import ParamModelService
from src.domain.services.v1.design_rule_engine_v1 import DesignRuleEngineV1
from src.domain.services.v1.airframe_gen_service import AirframeGenService
from src.domain.services.v1.structure_gen_service import StructureGenService
from src.domain.services.v1.powertrain_service import PowertrainService
from src.domain.services.v1.wire_harness_service import WireHarnessService


class TestParametricModel(unittest.TestCase):
    def test_create_model(self):
        model = ParametricModel(model_name="Test Model", model_type=ModelType.AIRFRAME)
        self.assertEqual(model.status, ModelStatus.DRAFT)
        self.assertEqual(model.model_type, ModelType.AIRFRAME)

    def test_update_parameters(self):
        model = ParametricModel()
        model.update_parameters({"wing_span_m": 3.0, "aspect_ratio": 8.0})
        self.assertEqual(model.parameters["wing_span_m"], 3.0)

    def test_cannot_update_released(self):
        model = ParametricModel(status=ModelStatus.RELEASED)
        with self.assertRaises(ValueError):
            model.update_parameters({"wing_span_m": 3.0})

    def test_mark_generated(self):
        model = ParametricModel()
        model.mark_generated()
        self.assertEqual(model.status, ModelStatus.GENERATED)
        self.assertEqual(len(model.domain_events), 1)

    def test_status_transitions(self):
        model = ParametricModel()
        model.mark_generated()
        model.mark_validated()
        model.mark_approved()
        model.mark_released()
        self.assertEqual(model.status, ModelStatus.RELEASED)

    def test_invalid_transition(self):
        model = ParametricModel()
        with self.assertRaises(ValueError):
            model.mark_released()


class TestAirframeModel(unittest.TestCase):
    def test_create_airframe(self):
        af = AirframeModel(
            fuselage_params=FuselageParams(length_m=1.5, diameter_m=0.2),
            wing_params=WingParams(span_m=2.0, aspect_ratio=8.0, area_m2=0.5),
            tail_params=TailParams(h_tail_area_m2=0.05, v_tail_area_m2=0.03),
        )
        self.assertEqual(af.fuselage_params.length_m, 1.5)
        self.assertEqual(af.wing_params.span_m, 2.0)

    def test_mark_generated(self):
        af = AirframeModel()
        af.mark_generated()
        self.assertEqual(len(af.domain_events), 1)
        self.assertEqual(af.domain_events[0]["event_type"], "airframe.generated")


class TestStructureModel(unittest.TestCase):
    def test_create_structure(self):
        s = StructureModel(
            component_type=StructureComponentType.SPAR,
            material="carbon_fiber",
            geometry={"type": "I_beam", "length_m": 1.0},
        )
        self.assertEqual(s.component_type, StructureComponentType.SPAR)

    def test_check_interference(self):
        s1 = StructureModel(
            geometry={"bounding_box": {"min_x": 0, "max_x": 1, "min_y": 0, "max_y": 1, "min_z": 0, "max_z": 1}},
            component_type=StructureComponentType.SPAR,
        )
        s2 = StructureModel(
            geometry={"bounding_box": {"min_x": 0.5, "max_x": 1.5, "min_y": 0, "max_y": 1, "min_z": 0, "max_z": 1}},
            component_type=StructureComponentType.RIB,
        )
        issues = s1.check_interference(s2)
        self.assertTrue(len(issues) > 0)

    def test_no_interference(self):
        s1 = StructureModel(
            geometry={"bounding_box": {"min_x": 0, "max_x": 1, "min_y": 0, "max_y": 1, "min_z": 0, "max_z": 1}},
            component_type=StructureComponentType.SPAR,
        )
        s2 = StructureModel(
            geometry={"bounding_box": {"min_x": 2, "max_x": 3, "min_y": 0, "max_y": 1, "min_z": 0, "max_z": 1}},
            component_type=StructureComponentType.RIB,
        )
        issues = s1.check_interference(s2)
        self.assertEqual(len(issues), 0)


class TestPowertrainModel(unittest.TestCase):
    def test_create_powertrain(self):
        pt = PowertrainModel(
            motor_spec=MotorSpec(max_thrust_n=50.0, kv_rating=600),
            battery_spec=BatterySpec(capacity_mah=5000, voltage_v=22.2),
        )
        self.assertEqual(pt.motor_spec.max_thrust_n, 50.0)

    def test_calculate_endurance(self):
        pt = PowertrainModel(
            battery_spec=BatterySpec(capacity_mah=5000, voltage_v=22.2),
        )
        endurance = pt.calculate_endurance(500.0)
        self.assertIsNotNone(endurance)
        self.assertTrue(endurance > 0)

    def test_calculate_max_thrust(self):
        pt = PowertrainModel(motor_spec=MotorSpec(max_thrust_n=50.0))
        total = pt.calculate_max_thrust(motor_count=4)
        self.assertEqual(total, 200.0)


class TestWireHarnessModel(unittest.TestCase):
    def test_add_wire(self):
        wh = WireHarnessModel()
        wh.add_wire(WireSpec(wire_id="W-001", gauge_awg=14, length_m=0.5))
        self.assertEqual(len(wh.wire_list), 1)

    def test_add_connector(self):
        wh = WireHarnessModel()
        wh.add_connector(ConnectorSpec(connector_id="CN-001", connector_type="xt90"))
        self.assertEqual(len(wh.connector_list), 1)

    def test_validate_routing(self):
        wh = WireHarnessModel()
        wh.add_wire(WireSpec(wire_id="W-001"))
        issues = wh.validate_routing()
        self.assertTrue(len(issues) > 0)

    def test_calculate_weight(self):
        wh = WireHarnessModel()
        wh.add_wire(WireSpec(wire_id="W-001", gauge_awg=14, length_m=1.0))
        weight = wh.calculate_total_weight()
        self.assertTrue(weight > 0)


class TestDesignRule(unittest.TestCase):
    def test_evaluate_pass(self):
        rule = DesignRule(
            rule_id="TEST-001",
            condition_expr="5 <= aspect_ratio <= 25",
            severity=RuleSeverity.ERROR,
            enabled=True,
        )
        result = rule.evaluate({"aspect_ratio": 10})
        self.assertIsNone(result)

    def test_evaluate_fail(self):
        rule = DesignRule(
            rule_id="TEST-002",
            rule_name="Test Rule",
            condition_expr="5 <= aspect_ratio <= 25",
            severity=RuleSeverity.ERROR,
            description="AR must be 5-25",
            enabled=True,
        )
        result = rule.evaluate({"aspect_ratio": 2})
        self.assertIsNotNone(result)
        self.assertEqual(result.severity, RuleSeverity.ERROR)

    def test_disabled_rule(self):
        rule = DesignRule(rule_id="TEST-003", condition_expr="False", enabled=False)
        result = rule.evaluate({})
        self.assertIsNone(result)

    def test_builtin_rules_count(self):
        self.assertTrue(len(BUILTIN_DESIGN_RULES) >= 5)


class TestParamModelService(unittest.TestCase):
    def setUp(self):
        self.service = ParamModelService()

    def test_generate_model(self):
        model = self.service.generate_model({
            "aircraft_type": "fixed_wing",
            "payload_kg": 10,
            "range_km": 100,
            "cruise_speed_kmh": 100,
        })
        self.assertEqual(model.status, ModelStatus.GENERATED)
        self.assertIn("mtow_estimate_kg", model.parameters)
        self.assertIn("wing_area_m2", model.parameters)

    def test_update_model_propagation(self):
        model = self.service.generate_model({"payload_kg": 10})
        self.service.update_model(model, {"wing_span_m": 3.0, "aspect_ratio": 10.0})
        self.assertAlmostEqual(model.parameters["wing_area_m2"], 0.9, places=1)


class TestDesignRuleEngineV1(unittest.TestCase):
    def setUp(self):
        self.engine = DesignRuleEngineV1()

    def test_validate_airframe(self):
        violations = self.engine.validate({
            "aspect_ratio": 10,
            "sweep_angle_deg": 5,
            "taper_ratio": 0.5,
            "wing_loading": 150,
            "fineness_ratio": 8,
        }, domain="airframe")
        self.assertEqual(len(violations), 0)

    def test_validate_violations(self):
        violations = self.engine.validate({"aspect_ratio": 2, "wing_loading": 150, "fineness_ratio": 8})
        self.assertTrue(len(violations) > 0)

    def test_validate_incremental(self):
        violations = self.engine.validate_incremental(
            {"aspect_ratio": 2, "wing_loading": 150, "fineness_ratio": 8},
            ["aspect_ratio"],
        )
        self.assertTrue(len(violations) > 0)

    def test_add_custom_rule(self):
        self.engine.add_rule(DesignRule(
            rule_id="CUSTOM-001",
            condition_expr="wing_span_m <= 10",
            severity=RuleSeverity.WARNING,
            description="Span limit",
        ))
        rules = self.engine.get_rules()
        self.assertTrue(any(r.rule_id == "CUSTOM-001" for r in rules))

    def test_disable_rule(self):
        self.engine.disable_rule("AERO-001")
        rules = self.engine.get_rules()
        aero001 = next(r for r in rules if r.rule_id == "AERO-001")
        self.assertFalse(aero001.enabled)


class TestAirframeGenService(unittest.TestCase):
    def setUp(self):
        self.service = AirframeGenService()

    def test_generate_fixed_wing(self):
        af = self.service.generate_airframe({
            "aircraft_type": "fixed_wing",
            "payload_kg": 10,
            "cruise_speed_kmh": 100,
            "range_km": 200,
        })
        self.assertTrue(af.wing_params.span_m > 0)
        self.assertTrue(af.fuselage_params.length_m > 0)
        self.assertTrue(af.tail_params.h_tail_area_m2 > 0)

    def test_generate_evtol(self):
        af = self.service.generate_airframe({"aircraft_type": "evtol", "payload_kg": 200})
        self.assertTrue(af.wing_params.span_m > 0)


class TestStructureGenService(unittest.TestCase):
    def setUp(self):
        self.service = StructureGenService()

    def test_generate_structures(self):
        structures = self.service.generate_structure({
            "wing_span_m": 2.0,
            "root_chord_m": 0.3,
            "fuselage_length_m": 1.5,
        })
        self.assertTrue(len(structures) > 0)
        spar_count = sum(1 for s in structures if s.component_type == StructureComponentType.SPAR)
        self.assertEqual(spar_count, 1)
        rib_count = sum(1 for s in structures if s.component_type == StructureComponentType.RIB)
        self.assertTrue(rib_count >= 3)


class TestPowertrainService(unittest.TestCase):
    def setUp(self):
        self.service = PowertrainService()

    def test_generate_electric(self):
        pt = self.service.generate_powertrain({
            "power_type": "electric",
            "payload_kg": 10,
            "cruise_speed_kmh": 100,
            "range_km": 50,
        })
        self.assertTrue(pt.motor_spec.max_thrust_n > 0)
        self.assertTrue(pt.battery_spec.capacity_mah > 0)
        self.assertIn("thrust_to_weight_ratio", pt.thrust_params)

    def test_generate_evtol(self):
        pt = self.service.generate_powertrain({
            "aircraft_type": "evtol",
            "power_type": "electric",
            "payload_kg": 200,
            "cruise_speed_kmh": 150,
            "range_km": 100,
            "motor_count": 8,
        })
        self.assertEqual(pt.thrust_params["motor_count"], 8)


class TestWireHarnessService(unittest.TestCase):
    def setUp(self):
        self.service = WireHarnessService()

    def test_generate_harness(self):
        wh = self.service.generate_wire_harness({"motor_count": 4})
        self.assertTrue(len(wh.wire_list) > 0)
        self.assertTrue(len(wh.routing_paths) > 0)

    def test_generate_with_powertrain(self):
        wh = self.service.generate_wire_harness(
            {"motor_count": 2},
            {"motor_count": 2, "battery_voltage": 22.2, "max_current_a": 30},
        )
        self.assertTrue(len(wh.wire_list) >= 2)


if __name__ == "__main__":
    unittest.main()