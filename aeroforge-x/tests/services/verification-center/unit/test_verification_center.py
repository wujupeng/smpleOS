import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'services', 'verification-center'))

import math
import unittest

from src.domain.entities.stability_analysis import StabilityAnalysis, StabilityResult, ParameterSuggestion
from src.domain.entities.flight_dynamics_analysis import FlightDynamicsAnalysis, TrimResult, SimulationState, DynamicResponseResult
from src.domain.entities.control_synthesis_result import ControlSynthesisResult, PIDParams, LQRParams, MPCParams, StabilityMargins
from src.domain.entities.flight_envelope_analysis import FlightEnvelopeAnalysis, LimitSpeeds, LimitLoadFactors, VnDiagramPoint, EnvelopeViolation
from src.domain.services.stability_engine import StabilityEngine
from src.domain.services.flight_dynamics_engine import FlightDynamicsEngine
from src.domain.services.control_synthesis_engine import ControlSynthesisEngine
from src.domain.services.flight_envelope_engine import FlightEnvelopeEngine


class TestStabilityEngine(unittest.TestCase):
    def setUp(self):
        self.engine = StabilityEngine()
        self.config = {
            "wing_area_m2": 0.5, "wing_span_m": 2.0, "h_tail_area_m2": 0.05,
            "h_tail_arm_m": 0.6, "v_tail_area_m2": 0.03, "cg_position_pct_mac": 25.0,
            "ac_position_pct_mac": 25.0, "dihedral_angle_deg": 3.0, "sweep_angle_deg": 2.0,
        }

    def test_longitudinal_stability(self):
        result = self.engine.analyze_longitudinal_stability(self.config)
        self.assertIsNotNone(result.static_margin_pct_mac)
        self.assertIsNotNone(result.neutral_point_pct_mac)
        self.assertIsInstance(result.is_longitudinally_stable, bool)

    def test_lateral_stability(self):
        result = self.engine.analyze_lateral_stability(self.config)
        self.assertIsNotNone(result.roll_stiffness_derivative)
        self.assertIsNotNone(result.dutch_roll_damping_ratio)

    def test_directional_stability(self):
        result = self.engine.analyze_directional_stability(self.config)
        self.assertIsNotNone(result.yaw_stiffness_derivative)
        self.assertIsInstance(result.is_directionally_stable, bool)

    def test_suggest_adjustments(self):
        analysis = StabilityAnalysis(
            aircraft_config=self.config,
            longitudinal_result=StabilityResult(is_longitudinally_stable=False, static_margin_pct_mac=2.0),
            lateral_result=StabilityResult(is_laterally_stable=True),
            directional_result=StabilityResult(is_directionally_stable=True),
        )
        suggestions = self.engine.suggest_parameter_adjustments(analysis)
        self.assertTrue(len(suggestions) > 0)

    def test_full_analysis(self):
        analysis = self.engine.run_full_analysis(self.config)
        self.assertEqual(analysis.status, "completed")
        self.assertIsInstance(analysis.is_statically_unstable, bool)
        self.assertEqual(len(analysis.domain_events), 1)

    def test_unstable_detection(self):
        unstable_config = dict(self.config, cg_position_pct_mac=45.0)
        analysis = self.engine.run_full_analysis(unstable_config)
        self.assertTrue(analysis.is_statically_unstable)


class TestFlightDynamicsEngine(unittest.TestCase):
    def setUp(self):
        self.engine = FlightDynamicsEngine()
        self.config = {"mtow_kg": 25, "wing_area_m2": 0.5, "cruise_speed_ms": 30}

    def test_trim_analysis(self):
        result = self.engine.perform_trim_analysis(self.config, "cruise")
        self.assertIsNotNone(result.alpha_deg)
        self.assertIsNotNone(result.converged)
        self.assertEqual(result.trim_type, "cruise")

    def test_6dof_simulation(self):
        states = self.engine.run_6dof_simulation(self.config, duration_s=2.0, dt=0.02)
        self.assertTrue(len(states) > 0)
        self.assertEqual(states[0].time_s, 0.0)

    def test_dynamic_response(self):
        result = self.engine.analyze_dynamic_response(self.config, "step")
        self.assertTrue(result.settling_time_s > 0)
        self.assertTrue(result.rise_time_s > 0)
        self.assertTrue(len(result.modes) >= 2)

    def test_full_analysis(self):
        analysis = self.engine.run_full_analysis(self.config)
        self.assertEqual(analysis.status, "completed")
        self.assertTrue(len(analysis.trim_results) > 0)
        self.assertTrue(len(analysis.dynamic_response_results) > 0)


class TestControlSynthesisEngine(unittest.TestCase):
    def setUp(self):
        self.engine = ControlSynthesisEngine()
        self.config = {"natural_frequency_hz": 1.5, "damping_ratio": 0.5, "time_constant_s": 0.1,
                       "state_dimension": 4, "input_dimension": 1}

    def test_pid_generation(self):
        result = self.engine.generate_pid_control_law(self.config)
        self.assertTrue(result.pid_params.kp > 0)
        self.assertTrue(result.pid_params.ki > 0)
        self.assertTrue(result.pid_params.kd > 0)
        self.assertEqual(result.control_type, "pid")

    def test_lqr_generation(self):
        result = self.engine.generate_lqr_control_law(self.config)
        self.assertTrue(len(result.lqr_params.gain_matrix) > 0)
        self.assertTrue(result.stability_margins.gain_margin_db >= 6.0)

    def test_mpc_generation(self):
        result = self.engine.generate_mpc_control_law(self.config)
        self.assertTrue(result.mpc_params.prediction_horizon > 0)
        self.assertTrue(result.stability_margins.is_sufficient)

    def test_validate_margins(self):
        result = self.engine.generate_pid_control_law(self.config)
        is_valid = self.engine.validate_stability_margins(result)
        self.assertIsInstance(is_valid, bool)

    def test_iterate_control_law(self):
        result = ControlSynthesisResult(
            aircraft_config=self.config,
            control_type="pid",
            stability_margins=StabilityMargins(gain_margin_db=3.0, phase_margin_deg=30.0, is_sufficient=False),
        )
        iterated = self.engine.iterate_control_law(result)
        self.assertTrue(iterated.iteration_count > 0)

    def test_compare_alternatives(self):
        comparison = self.engine.compare_control_law_alternatives(self.config)
        self.assertIn("pid", comparison)
        self.assertIn("lqr", comparison)
        self.assertIn("mpc", comparison)
        self.assertIn("recommendation", comparison)


class TestFlightEnvelopeEngine(unittest.TestCase):
    def setUp(self):
        self.engine = FlightEnvelopeEngine()
        self.config = {"mtow_kg": 25, "wing_area_m2": 0.5, "cruise_speed_kmh": 100, "cl_max": 1.5, "cl_max_flap": 2.0}

    def test_compute_limit_speeds(self):
        speeds = self.engine.compute_limit_speeds(self.config)
        self.assertTrue(speeds.vs1_ms > 0)
        self.assertTrue(speeds.vc_ms > speeds.vs1_ms)
        self.assertTrue(speeds.vd_ms > speeds.vc_ms)
        self.assertTrue(speeds.vne_ms > 0)

    def test_compute_limit_load_factors(self):
        loads = self.engine.compute_limit_load_factors(self.config)
        self.assertTrue(loads.n_max_positive > 0)
        self.assertTrue(loads.n_max_negative < 0)
        self.assertTrue(loads.n_ultimate_positive > loads.n_max_positive)

    def test_generate_vn_diagram(self):
        speeds = self.engine.compute_limit_speeds(self.config)
        loads = self.engine.compute_limit_load_factors(self.config)
        diagram = self.engine.generate_vn_diagram(speeds, loads)
        self.assertTrue(len(diagram) >= 5)

    def test_overlay_gust_envelope(self):
        speeds = self.engine.compute_limit_speeds(self.config)
        gust = self.engine.overlay_gust_envelope(speeds, self.config)
        self.assertTrue(len(gust) >= 4)

    def test_detect_violations(self):
        speeds = LimitSpeeds(vne_ms=20.0)
        loads = LimitLoadFactors(n_max_positive=2.0, n_max_negative=-0.5)
        points = [VnDiagramPoint(speed_ms=25.0, load_factor=3.0, label="test")]
        violations = self.engine.detect_envelope_violations(points, [], speeds, loads)
        self.assertTrue(len(violations) > 0)

    def test_full_analysis(self):
        analysis = self.engine.run_full_analysis(self.config)
        self.assertEqual(analysis.status, "completed")
        self.assertTrue(len(analysis.vn_diagram) > 0)
        self.assertIsInstance(analysis.is_airworthy, bool)
        self.assertEqual(len(analysis.domain_events), 1)


if __name__ == "__main__":
    unittest.main()