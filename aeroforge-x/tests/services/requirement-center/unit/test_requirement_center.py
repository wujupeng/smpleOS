import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'services', 'requirement-center'))

from decimal import Decimal
import unittest

from src.domain.value_objects.enums import (
    AircraftType, SpecStatus, PowerType, ParameterCategory, ParameterPriority,
    TraceType, TraceSourceType,
)
from src.domain.entities.aircraft_spec import AircraftSpec, SpecParameter
from src.domain.entities.requirement_trace import RequirementTrace
from src.domain.services.spec_service import SpecService
from src.domain.services.requirement_trace_service import RequirementTraceService
from src.domain.services.sensitivity_analysis_service import SensitivityAnalysisService


class TestAircraftSpec(unittest.TestCase):
    def test_create_spec(self):
        spec = AircraftSpec(
            spec_number="AAF-SPEC-001",
            aircraft_type=AircraftType.FIXED_WING,
            payload_kg=Decimal("120"),
            range_km=Decimal("200"),
            cruise_speed_kmh=Decimal("150"),
            power_type=PowerType.ELECTRIC,
        )
        self.assertEqual(spec.status, SpecStatus.DRAFT)
        self.assertEqual(spec.aircraft_type, AircraftType.FIXED_WING)
        self.assertEqual(spec.payload_kg, Decimal("120"))

    def test_submit_for_review(self):
        spec = AircraftSpec(status=SpecStatus.DRAFT)
        param = SpecParameter(name="payload", is_required=True, value=Decimal("100"), category=ParameterCategory.PERFORMANCE)
        spec.add_parameter(param)
        spec.submit_for_review()
        self.assertEqual(spec.status, SpecStatus.SUBMITTED)

    def test_submit_missing_required(self):
        spec = AircraftSpec(status=SpecStatus.DRAFT)
        param = SpecParameter(name="payload", is_required=True, value=None, category=ParameterCategory.PERFORMANCE)
        spec.add_parameter(param)
        with self.assertRaises(ValueError):
            spec.submit_for_review()

    def test_approve_spec(self):
        spec = AircraftSpec(status=SpecStatus.SUBMITTED)
        spec.approve("user-001")
        self.assertEqual(spec.status, SpecStatus.APPROVED)
        self.assertEqual(spec.approved_by, "user-001")

    def test_confirm_spec(self):
        spec = AircraftSpec(status=SpecStatus.APPROVED, spec_id="s1", spec_number="AAF-SPEC-001")
        spec.confirm()
        self.assertEqual(spec.status, SpecStatus.CONFIRMED)
        self.assertIsNotNone(spec.confirmed_at)
        self.assertEqual(len(spec.domain_events), 1)
        self.assertEqual(spec.domain_events[0]["event_type"], "aircraft.spec.confirmed")

    def test_freeze_spec(self):
        spec = AircraftSpec(status=SpecStatus.CONFIRMED)
        spec.freeze()
        self.assertEqual(spec.status, SpecStatus.FROZEN)
        self.assertIsNotNone(spec.frozen_at)

    def test_reject_spec(self):
        spec = AircraftSpec(status=SpecStatus.SUBMITTED)
        spec.reject()
        self.assertEqual(spec.status, SpecStatus.REJECTED)

    def test_cannot_update_frozen(self):
        spec = AircraftSpec(status=SpecStatus.FROZEN)
        with self.assertRaises(ValueError):
            spec.update_parameters(payload_kg=Decimal("200"))

    def test_add_parameter(self):
        spec = AircraftSpec(status=SpecStatus.DRAFT)
        param = SpecParameter(name="wing_span", value=Decimal("2.5"), unit="m")
        spec.add_parameter(param)
        self.assertEqual(len(spec.parameters), 1)

    def test_update_parameter(self):
        spec = AircraftSpec(status=SpecStatus.DRAFT)
        param = SpecParameter(name="wing_span", value=Decimal("2.5"), unit="m")
        spec.add_parameter(param)
        spec.update_parameter(param.parameter_id, Decimal("3.0"))
        self.assertEqual(param.value, Decimal("3.0"))

    def test_remove_parameter(self):
        spec = AircraftSpec(status=SpecStatus.DRAFT)
        param = SpecParameter(name="wing_span", value=Decimal("2.5"))
        spec.add_parameter(param)
        spec.remove_parameter(param.parameter_id)
        self.assertEqual(len(spec.parameters), 0)

    def test_clear_events(self):
        spec = AircraftSpec(status=SpecStatus.APPROVED, spec_id="s1", spec_number="AAF-SPEC-001")
        spec.confirm()
        events = spec.clear_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(len(spec.domain_events), 0)


class TestSpecParameter(unittest.TestCase):
    def test_validate_range_rule(self):
        param = SpecParameter(
            name="wing_span",
            value=Decimal("50"),
            validation_rules=[{"type": "range", "min": 1, "max": 30}],
        )
        violations = param.validate()
        self.assertEqual(len(violations), 1)

    def test_validate_required_rule(self):
        param = SpecParameter(name="payload", value=None, validation_rules=[{"type": "required"}])
        violations = param.validate()
        self.assertEqual(len(violations), 1)

    def test_validate_pass(self):
        param = SpecParameter(
            name="wing_span",
            value=Decimal("2.5"),
            validation_rules=[{"type": "range", "min": 0.5, "max": 30}],
        )
        violations = param.validate()
        self.assertEqual(len(violations), 0)


class TestSpecService(unittest.TestCase):
    def setUp(self):
        self.service = SpecService()

    def test_create_spec(self):
        spec = self.service.create_spec(
            aircraft_type=AircraftType.FIXED_WING,
            created_by="user-001",
            payload_kg=Decimal("120"),
            range_km=Decimal("200"),
        )
        self.assertIsNotNone(spec.spec_id)
        self.assertTrue(spec.spec_number.startswith("AAF-SPEC-"))
        self.assertEqual(spec.aircraft_type, AircraftType.FIXED_WING)

    def test_validate_spec_valid(self):
        spec = AircraftSpec(
            payload_kg=Decimal("120"),
            range_km=Decimal("200"),
            cruise_speed_kmh=Decimal("150"),
            power_type=PowerType.ELECTRIC,
        )
        violations = self.service.validate_spec(spec)
        self.assertEqual(len([v for v in violations if v["severity"] == "error"]), 0)

    def test_validate_spec_negative_payload(self):
        spec = AircraftSpec(payload_kg=Decimal("-10"))
        violations = self.service.validate_spec(spec)
        self.assertTrue(any(v["parameter"] == "payload_kg" for v in violations))

    def test_validate_spec_electric_speed_warning(self):
        spec = AircraftSpec(
            power_type=PowerType.ELECTRIC,
            cruise_speed_kmh=Decimal("500"),
        )
        violations = self.service.validate_spec(spec)
        self.assertTrue(any(v["parameter"] == "cruise_speed_kmh" for v in violations))

    def test_confirm_spec(self):
        spec = AircraftSpec(
            status=SpecStatus.APPROVED,
            spec_id="s1",
            spec_number="AAF-SPEC-001",
            payload_kg=Decimal("120"),
            range_km=Decimal("200"),
            cruise_speed_kmh=Decimal("150"),
        )
        self.service.confirm_spec(spec)
        self.assertEqual(spec.status, SpecStatus.CONFIRMED)

    def test_confirm_with_critical_violations(self):
        spec = AircraftSpec(status=SpecStatus.APPROVED, payload_kg=Decimal("-10"))
        with self.assertRaises(ValueError):
            self.service.confirm_spec(spec)

    def test_derive_constraints(self):
        spec = AircraftSpec(
            payload_kg=Decimal("100"),
            range_km=Decimal("200"),
            cruise_speed_kmh=Decimal("100"),
            power_type=PowerType.ELECTRIC,
        )
        constraints = self.service.derive_constraints(spec)
        self.assertIn("payload_range_product", constraints)
        self.assertIn("endurance_hours", constraints)
        self.assertIn("mtow_estimate_kg", constraints)
        self.assertIn("battery_energy_estimate_kwh", constraints)
        self.assertEqual(constraints["payload_range_product"], 20000.0)


class TestRequirementTrace(unittest.TestCase):
    def test_create_trace(self):
        trace = RequirementTrace(
            source_type=TraceSourceType.SPEC,
            source_id="spec-001",
            target_type=TraceSourceType.DESIGN_OBJECT,
            target_id="design-001",
            trace_type=TraceType.SATISFIES,
        )
        self.assertEqual(trace.source_type, TraceSourceType.SPEC)
        self.assertEqual(trace.confidence, Decimal("1.00"))

    def test_validate_trace(self):
        trace = RequirementTrace(source_id="", target_id="t1")
        violations = trace.validate()
        self.assertTrue(len(violations) > 0)

    def test_self_reference_invalid(self):
        trace = RequirementTrace(
            source_type=TraceSourceType.SPEC,
            source_id="same-id",
            target_type=TraceSourceType.SPEC,
            target_id="same-id",
        )
        violations = trace.validate()
        self.assertTrue(any("Self-referencing" in v for v in violations))


class TestRequirementTraceService(unittest.TestCase):
    def setUp(self):
        self.service = RequirementTraceService()

    def test_create_trace(self):
        trace = self.service.create_trace(
            source_type=TraceSourceType.SPEC,
            source_id="spec-001",
            target_type=TraceSourceType.DESIGN_OBJECT,
            target_id="design-001",
            trace_type=TraceType.SATISFIES,
        )
        self.assertIsNotNone(trace.trace_id)

    def test_get_trace_chain(self):
        self.service.create_trace(TraceSourceType.SPEC, "s1", TraceSourceType.DESIGN_OBJECT, "d1", TraceType.SATISFIES)
        self.service.create_trace(TraceSourceType.SPEC, "d1", TraceSourceType.TEST_CASE, "t1", TraceType.VERIFIES)
        chain = self.service.get_trace_chain("s1")
        self.assertTrue(len(chain) >= 1)

    def test_verify_trace_completeness(self):
        self.service.create_trace(TraceSourceType.SPEC, "s1", TraceSourceType.DESIGN_OBJECT, "d1", TraceType.SATISFIES)
        result = self.service.verify_trace_completeness(
            TraceSourceType.SPEC, "s1",
            [TraceSourceType.DESIGN_OBJECT, TraceSourceType.TEST_CASE],
        )
        self.assertLess(result["completeness"], 1.0)
        self.assertIn("test_case", result["missing_target_types"])


class TestSensitivityAnalysisService(unittest.TestCase):
    def setUp(self):
        self.service = SensitivityAnalysisService()

    def test_run_sensitivity(self):
        spec = AircraftSpec(
            payload_kg=Decimal("100"),
            range_km=Decimal("200"),
            cruise_speed_kmh=Decimal("100"),
            takeoff_distance_m=Decimal("50"),
        )
        spec.parameters = [
            SpecParameter(name="payload_kg", value=Decimal("100")),
            SpecParameter(name="range_km", value=Decimal("200")),
        ]
        results = self.service.run_sensitivity_analysis(spec, ["payload_kg", "range_km"])
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].influence_rank, 1)
        self.assertTrue(results[0].sensitivity_index >= 0)

    def test_empty_parameters(self):
        spec = AircraftSpec()
        results = self.service.run_sensitivity_analysis(spec, [])
        self.assertEqual(len(results), 0)


if __name__ == "__main__":
    unittest.main()