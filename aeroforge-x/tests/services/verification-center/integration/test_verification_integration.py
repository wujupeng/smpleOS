import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'services', 'verification-center'))

import unittest

from src.domain.services.stability_engine import StabilityEngine
from src.domain.services.flight_dynamics_engine import FlightDynamicsEngine
from src.domain.services.control_synthesis_engine import ControlSynthesisEngine
from src.domain.services.flight_envelope_engine import FlightEnvelopeEngine


class TestStabilityToParameterAdjustmentIntegration(unittest.TestCase):
    def test_unstable_to_suggestions(self):
        engine = StabilityEngine()
        config = {
            "wing_area_m2": 0.5, "wing_span_m": 2.0, "h_tail_area_m2": 0.02,
            "h_tail_arm_m": 0.3, "v_tail_area_m2": 0.01, "cg_position_pct_mac": 40.0,
            "ac_position_pct_mac": 25.0, "dihedral_angle_deg": 0.0, "sweep_angle_deg": 10.0,
        }
        analysis = engine.run_full_analysis(config)
        self.assertTrue(analysis.is_statically_unstable)
        self.assertTrue(len(analysis.suggestions) > 0)


class Test6DOFToControlSynthesisIntegration(unittest.TestCase):
    def test_dynamics_to_control_law(self):
        fd_engine = FlightDynamicsEngine()
        cs_engine = ControlSynthesisEngine()
        config = {"mtow_kg": 25, "wing_area_m2": 0.5, "cruise_speed_ms": 30}
        fd_analysis = fd_engine.run_full_analysis(config)
        self.assertEqual(fd_analysis.status, "completed")
        ctrl_config = {
            "natural_frequency_hz": fd_analysis.dynamic_response_results[0].natural_frequency_hz,
            "damping_ratio": fd_analysis.dynamic_response_results[0].damping_ratio,
            "state_dimension": 4, "input_dimension": 1,
        }
        pid_result = cs_engine.generate_pid_control_law(ctrl_config)
        self.assertEqual(pid_result.status, "completed")
        lqr_result = cs_engine.generate_lqr_control_law(ctrl_config)
        self.assertTrue(lqr_result.stability_margins.is_sufficient)


class TestFlightEnvelopeAirworthinessIntegration(unittest.TestCase):
    def test_envelope_airworthiness(self):
        engine = FlightEnvelopeEngine()
        config = {"mtow_kg": 25, "wing_area_m2": 0.5, "cruise_speed_kmh": 100, "cl_max": 1.5}
        analysis = engine.run_full_analysis(config)
        self.assertEqual(analysis.status, "completed")
        self.assertIsInstance(analysis.is_airworthy, bool)


class TestCAEKnowledgeIntegration(unittest.TestCase):
    def test_stability_results_to_knowledge_format(self):
        engine = StabilityEngine()
        config = {"wing_area_m2": 0.5, "wing_span_m": 2.0, "h_tail_area_m2": 0.05,
                  "h_tail_arm_m": 0.6, "v_tail_area_m2": 0.03, "cg_position_pct_mac": 25.0}
        analysis = engine.run_full_analysis(config)
        events = analysis.clear_events()
        self.assertTrue(len(events) > 0)
        self.assertEqual(events[0]["event_type"], "stability.analysis.completed")
        self.assertIn("analysis_id", events[0])
        self.assertIn("is_statically_unstable", events[0])


if __name__ == "__main__":
    unittest.main()