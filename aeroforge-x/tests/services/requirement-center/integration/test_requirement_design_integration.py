import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'services', 'requirement-center'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'services', 'design-center'))

from decimal import Decimal
import unittest

from src.domain.value_objects.enums import AircraftType, SpecStatus, PowerType
from src.domain.entities.aircraft_spec import AircraftSpec, SpecParameter
from src.domain.services.spec_service import SpecService
from src.domain.services.v1.airframe_gen_service import AirframeGenService
from src.domain.services.v1.powertrain_service import PowertrainService
from src.domain.services.v1.structure_gen_service import StructureGenService
from src.domain.services.v1.wire_harness_service import WireHarnessService
from src.domain.services.v1.design_rule_engine_v1 import DesignRuleEngineV1


class TestSpecToDesignIntegration(unittest.TestCase):
    def test_spec_confirm_to_model_generation(self):
        spec_service = SpecService()
        spec = spec_service.create_spec(
            aircraft_type=AircraftType.FIXED_WING,
            created_by="user-001",
            payload_kg=Decimal("10"),
            range_km=Decimal("100"),
            cruise_speed_kmh=Decimal("80"),
            power_type=PowerType.ELECTRIC,
        )
        constraints = spec_service.derive_constraints(spec)
        spec.derived_constraints = constraints
        spec.submit_for_review()
        spec.approve("approver-001")
        spec.confirm()
        self.assertEqual(spec.status, SpecStatus.CONFIRMED)

        airframe_service = AirframeGenService()
        airframe = airframe_service.generate_airframe({
            "aircraft_type": spec.aircraft_type.value,
            "payload_kg": float(spec.payload_kg),
            "cruise_speed_kmh": float(spec.cruise_speed_kmh),
            "range_km": float(spec.range_km),
        })
        self.assertTrue(airframe.wing_params.span_m > 0)

        powertrain_service = PowertrainService()
        powertrain = powertrain_service.generate_powertrain({
            "aircraft_type": spec.aircraft_type.value,
            "power_type": spec.power_type.value,
            "payload_kg": float(spec.payload_kg),
            "cruise_speed_kmh": float(spec.cruise_speed_kmh),
            "range_km": float(spec.range_km),
            "mtow_estimate_kg": constraints.get("mtow_estimate_kg", 25),
        })
        self.assertTrue(powertrain.motor_spec.max_thrust_n > 0)

    def test_design_rule_validation_integration(self):
        engine = DesignRuleEngineV1()
        spec = AircraftSpec(
            payload_kg=Decimal("10"),
            range_km=Decimal("100"),
            cruise_speed_kmh=Decimal("80"),
            power_type=PowerType.ELECTRIC,
        )
        context = {
            "aspect_ratio": 10,
            "sweep_angle_deg": 5,
            "taper_ratio": 0.5,
            "wing_loading": 150,
            "fineness_ratio": 8,
            "thrust_to_weight": 0.5,
            "max_discharge_c": 50,
            "required_c_rating": 30,
            "wall_thickness_mm": 1.0,
        }
        violations = engine.validate(context)
        critical = [v for v in violations if v.severity.value in ("error", "critical")]
        self.assertEqual(len(critical), 0)

    def test_parameter_update_propagation(self):
        airframe_service = AirframeGenService()
        af1 = airframe_service.generate_airframe({"aircraft_type": "fixed_wing", "payload_kg": 10})
        af2 = airframe_service.generate_airframe({"aircraft_type": "fixed_wing", "payload_kg": 50})
        self.assertNotEqual(af1.wing_params.span_m, af2.wing_params.span_m)
        self.assertTrue(af2.wing_params.span_m > af1.wing_params.span_m)


class TestDesignRuleValidationIntegration(unittest.TestCase):
    def test_full_design_validation(self):
        engine = DesignRuleEngineV1()
        airframe_service = AirframeGenService()
        af = airframe_service.generate_airframe({"aircraft_type": "fixed_wing", "payload_kg": 10})
        context = {
            "aspect_ratio": af.wing_params.aspect_ratio,
            "sweep_angle_deg": af.wing_params.sweep_angle_deg,
            "taper_ratio": af.wing_params.taper_ratio,
            "wing_loading": 150,
            "fineness_ratio": af.fuselage_params.fineness_ratio,
            "thrust_to_weight": 0.5,
            "max_discharge_c": 50,
            "required_c_rating": 30,
            "wall_thickness_mm": 1.0,
        }
        violations = engine.validate(context)
        self.assertIsInstance(violations, list)


if __name__ == "__main__":
    unittest.main()