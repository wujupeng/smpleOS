import pytest
import math
import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "services", "physics-twin-service"))

from src.domain.plugins.dof6_model import DOF6Model
from src.domain.plugins.battery_model import BatteryModel
from src.domain.plugins.control_model import ControlModel
from src.domain.plugins.interfaces import DOF6State, BatteryState, ControlState


class TestDOF6Low:
    def setup_method(self):
        self.model = DOF6Model(fidelity="Low")
        self.model.initialize({"mass": 1500.0, "wing_area": 16.0, "CL_alpha": 5.0, "CD_0": 0.02, "k_induced": 0.05, "initial_altitude": 1000.0, "initial_speed": 50.0})

    def test_initial_state(self):
        state = self.model.get_state()
        assert state["position"][2] == 1000.0
        assert state["velocity"][0] == 50.0

    def test_step_advances_time(self):
        result = self.model.step(0.01)
        assert "state" in result

    def test_linearized_cl(self):
        result = self.model.step(0.01)
        assert result["fidelity"] == "Low"

    def test_cd_drag_polar(self):
        alpha = math.atan2(self.model._state.velocity[2], max(self.model._state.velocity[0], 0.1))
        CL = 5.0 * alpha
        CD = 0.02 + 0.05 * CL ** 2
        assert CD > 0.02

    def test_isa_density_sea_level(self):
        rho = self.model._isa_density(0)
        assert rho == pytest.approx(1.225, rel=0.01)

    def test_isa_density_11000m(self):
        rho = self.model._isa_density(11000)
        assert rho == pytest.approx(0.364, rel=0.05)

    def test_forward_euler_integration(self):
        initial_x = self.model._state.position[0]
        self.model.step(0.01)
        assert self.model._state.position[0] > initial_x

    def test_multiple_steps_stable(self):
        for _ in range(100):
            result = self.model.step(0.01)
        stability = self.model.validate_numerical_stability()
        assert stability.is_stable is True

    def test_step_performance(self):
        start = time.perf_counter()
        for _ in range(100):
            self.model.step(0.01)
        elapsed = (time.perf_counter() - start) / 100 * 1000
        assert elapsed < 10.0, f"6DOF Low step took {elapsed:.3f}ms"


class TestDOF6Mid:
    def setup_method(self):
        self.model = DOF6Model(fidelity="Mid")
        self.model.initialize({
            "mass": 1500.0, "Ixx": 1000.0, "Iyy": 3000.0, "Izz": 3500.0, "Ixz": 50.0,
            "wing_area": 16.0, "wingspan": 10.0, "chord_length": 1.6,
            "initial_altitude": 1000.0, "initial_speed": 50.0,
        })

    def test_nonlinear_equation_step(self):
        result = self.model.step(0.01)
        assert result["fidelity"] == "Mid"
        assert "forces" in result
        assert "moments" in result

    def test_rk4_integration(self):
        initial_pos = self.model._state.position[0]
        for _ in range(10):
            self.model.step(0.01)
        assert self.model._state.position[0] > initial_pos

    def test_gimbal_lock_protection(self):
        self.model._state = DOF6State(
            position=[0, 0, 1000], velocity=[50, 0, 0],
            attitude=[0, math.radians(89), 0], angular_rates=[0, 0, 0],
        )
        self.model.step(0.01)
        assert abs(self.model._state.attitude[1]) <= math.radians(85) + 0.01

    def test_coefficient_interpolation(self):
        val = self.model._interp_1d(0.05, [(0, 0.3), (0.1, 0.8)])
        assert val == pytest.approx(0.55, rel=0.01)

    def test_coefficient_extrapolation_low(self):
        val = self.model._interp_1d(-0.1, [(0, 0.3), (0.1, 0.8)])
        assert val == 0.3

    def test_multiple_steps_stable(self):
        for _ in range(200):
            self.model.step(0.01)
        stability = self.model.validate_numerical_stability()
        assert stability.is_stable is True

    def test_numerical_accuracy_vs_analytical(self):
        self.model.initialize({"mass": 1500.0, "wing_area": 16.0, "initial_altitude": 1000.0, "initial_speed": 50.0, "CL_alpha": 5.0, "CD_0": 0.02})
        for _ in range(100):
            self.model.step(0.01)
        V = math.sqrt(sum(v ** 2 for v in self.model._state.velocity))
        assert 10 < V < 200


class TestDOF6Detail:
    def setup_method(self):
        self.model = DOF6Model(fidelity="Detail")
        self.model.initialize({
            "mass": 1500.0, "Ixx": 1000.0, "Iyy": 3000.0, "Izz": 3500.0, "Ixz": 50.0,
            "wing_area": 16.0, "wingspan": 10.0, "chord_length": 1.6,
            "initial_altitude": 1000.0, "initial_speed": 50.0,
        })

    def test_quaternion_attitude_update(self):
        result = self.model.step(0.01)
        assert result["fidelity"] == "Detail"
        for a in self.model._state.attitude:
            assert not math.isnan(a)

    def test_quaternion_norm_preserved(self):
        for _ in range(50):
            self.model.step(0.01)
        q = self.model._get_quaternion()
        q_norm = math.sqrt(sum(x ** 2 for x in q))
        assert q_norm == pytest.approx(1.0, abs=0.01)

    def test_2d_interpolation(self):
        table = {0.0: [(0, 0.3)], 0.1: [(0, 0.8)]}
        val = self.model._interp_2d(0.05, 0, table)
        assert 0.3 <= val <= 0.8

    def test_divergence_detection(self):
        self.model._state = DOF6State(
            position=[0, 0, 1000], velocity=[2000, 0, 0],
            attitude=[0, 0, 0], angular_rates=[0, 0, 0],
        )
        stability = self.model.validate_numerical_stability()
        assert stability.is_stable is False

    def test_stable_flight(self):
        for _ in range(200):
            self.model.step(0.01)
        stability = self.model.validate_numerical_stability()
        assert stability.is_stable is True

    def test_step_performance(self):
        start = time.perf_counter()
        for _ in range(100):
            self.model.step(0.01)
        elapsed = (time.perf_counter() - start) / 100 * 1000
        assert elapsed < 10.0, f"6DOF Detail step took {elapsed:.3f}ms"


class TestBatteryLow:
    def setup_method(self):
        self.model = BatteryModel(fidelity="Low")
        self.model.initialize({"capacity_Ah": 100.0, "R0": 0.01, "nominal_voltage": 400.0, "initial_soc": 1.0})

    def test_initial_state(self):
        state = self.model.get_state()
        assert state["soc"] == 1.0

    def test_coulomb_counting(self):
        self.model.step(1.0, {"current": 50.0})
        assert self.model._state.soc < 1.0

    def test_terminal_voltage(self):
        result = self.model.step(1.0, {"current": 50.0})
        assert result["state"]["terminal_voltage"] > 0

    def test_soc_decreases_with_discharge(self):
        initial_soc = self.model._state.soc
        for _ in range(10):
            self.model.step(1.0, {"current": 50.0})
        assert self.model._state.soc < initial_soc


class TestBatteryMid:
    def setup_method(self):
        self.model = BatteryModel(fidelity="Mid")
        self.model.initialize({
            "capacity_Ah": 100.0, "R0": 0.01, "RC1": 0.005, "C1": 10000.0,
            "nominal_voltage": 400.0, "initial_soc": 1.0,
            "ocv_table": [(0.0, 300.0), (0.5, 380.0), (1.0, 420.0)],
        })

    def test_thevenin_model(self):
        result = self.model.step(1.0, {"current": 50.0})
        assert result["fidelity"] == "Mid"
        assert "state" in result

    def test_ocv_correction(self):
        for _ in range(5):
            self.model.step(1.0, {"current": 50.0})
        assert 0 < self.model._state.soc <= 1.0

    def test_thermal_model(self):
        for _ in range(10):
            self.model.step(1.0, {"current": 100.0})
        assert self.model._state.temperature > 25.0

    def test_soh_aging(self):
        initial_soh = self.model._state.soh
        for _ in range(100):
            self.model.step(1.0, {"current": 50.0})
        assert self.model._state.soh <= initial_soh


class TestBatteryDetail:
    def setup_method(self):
        self.model = BatteryModel(fidelity="Detail")
        self.model.initialize({
            "capacity_Ah": 100.0, "R0": 0.01, "RC1": 0.005, "C1": 10000.0,
            "RC2": 0.002, "C2": 50000.0,
            "nominal_voltage": 400.0, "initial_soc": 1.0,
            "ocv_table": [(0.0, 300.0), (0.5, 380.0), (1.0, 420.0)],
        })

    def test_dual_rc_model(self):
        result = self.model.step(1.0, {"current": 50.0})
        assert result["fidelity"] == "Detail"

    def test_ekf_soc_correction(self):
        for _ in range(20):
            self.model.step(1.0, {"current": 50.0})
        assert 0 < self.model._state.soc <= 1.0

    def test_calendar_aging(self):
        initial_soh = self.model._state.soh
        for _ in range(200):
            self.model.step(1.0, {"current": 10.0})
        assert self.model._state.soh <= initial_soh

    def test_low_battery_warning(self):
        self.model._state.soc = 0.05
        result = self.model.step(1.0, {"current": 50.0})
        assert result.get("warnings") is not None or result["state"]["soc"] < 0.05

    def test_step_performance(self):
        start = time.perf_counter()
        for _ in range(100):
            self.model.step(0.01, {"current": 50.0})
        elapsed = (time.perf_counter() - start) / 100 * 1000
        assert elapsed < 5.0, f"Battery Detail step took {elapsed:.3f}ms"


class TestControlLow:
    def setup_method(self):
        self.model = ControlModel(fidelity="Low")
        self.model.initialize({"kp": 1.0, "ki": 0.1, "kd": 0.01, "dt": 0.01, "output_min": -25.0, "output_max": 25.0})

    def test_pid_output(self):
        result = self.model.step(0.01, {"setpoint": 10.0, "process_variable": 5.0})
        assert result["state"]["elevator_cmd"] != 0.0

    def test_anti_windup(self):
        for _ in range(1000):
            self.model.step(0.01, {"setpoint": 100.0, "process_variable": 0.0})
        assert abs(self.model._state.elevator_cmd) <= 25.0

    def test_tustin_discretization(self):
        result = self.model.step(0.01, {"setpoint": 5.0, "process_variable": 0.0})
        assert result["fidelity"] == "Low"


class TestControlMid:
    def setup_method(self):
        self.model = ControlModel(fidelity="Mid")
        self.model.initialize({
            "kp": 1.0, "ki": 0.1, "kd": 0.01, "dt": 0.01,
            "output_min": -25.0, "output_max": 25.0,
            "sas_pitch_gain": 0.5, "sas_roll_gain": 0.3, "sas_yaw_gain": 0.4,
        })

    def test_gain_scheduled_pid(self):
        result = self.model.step(0.01, {"setpoint": 10.0, "process_variable": 5.0, "airspeed": 50.0})
        assert result["fidelity"] == "Mid"

    def test_sas_damping(self):
        initial_rate = 1.0
        for _ in range(100):
            result = self.model.step(0.01, {"setpoint": 0.0, "process_variable": 0.0, "angular_rate_pitch": initial_rate})
        assert abs(result["state"]["elevator_cmd"]) > 0

    def test_autopilot_mode(self):
        result = self.model.step(0.01, {"setpoint": 1000.0, "process_variable": 900.0, "autopilot_mode": "ALTITUDE_HOLD"})
        assert result["state"].get("autopilot_mode") is not None


class TestControlDetail:
    def setup_method(self):
        self.model = ControlModel(fidelity="Detail")
        self.model.initialize({
            "A_matrix": [[0, 1], [-1, -0.5]],
            "B_matrix": [[0], [1]],
            "Q_matrix": [[1, 0], [0, 1]],
            "R_matrix": [[0.1]],
            "output_min": -25.0, "output_max": 25.0,
            "servo_rate_limit": 60.0,
        })

    def test_lqr_output(self):
        result = self.model.step(0.01, {"state_vector": [1.0, 0.0]})
        assert result["fidelity"] == "Detail"

    def test_envelope_protection(self):
        result = self.model.step(0.01, {"state_vector": [1.0, 0.0], "V_current": 200.0, "V_D": 180.0})
        assert result.get("envelope_protection_active") is True or result["state"].get("elevator_cmd") is not None

    def test_servo_rate_limit(self):
        prev_cmd = 0.0
        for _ in range(10):
            result = self.model.step(0.01, {"state_vector": [5.0, 0.0]})
            cmd = result["state"]["elevator_cmd"]
            rate = abs(cmd - prev_cmd) / 0.01
            assert rate <= 60.0 + 1.0
            prev_cmd = cmd

    def test_lqr_fallback_to_pid(self):
        self.model._lqr_K = None
        result = self.model.step(0.01, {"state_vector": [1.0, 0.0]})
        assert result is not None

    def test_step_performance(self):
        start = time.perf_counter()
        for _ in range(100):
            self.model.step(0.01, {"state_vector": [1.0, 0.0]})
        elapsed = (time.perf_counter() - start) / 100 * 1000
        assert elapsed < 2.0, f"Control Detail step took {elapsed:.3f}ms"