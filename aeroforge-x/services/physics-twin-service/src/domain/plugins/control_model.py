from __future__ import annotations

import math
from typing import Any

import numpy as np

from src.domain.plugins.interfaces import ControlOutput, ControlState, IPhysicsModelPlugin


class ControlModel(IPhysicsModelPlugin):

    def __init__(self, fidelity: str = "Low"):
        self.fidelity = fidelity
        self._state = ControlState()
        self._time = 0.0
        self._params: dict[str, Any] = {}
        self._integral = [0.0, 0.0, 0.0]
        self._prev_error = [0.0, 0.0, 0.0]

    def initialize(self, params: dict[str, Any]) -> None:
        self._params = params
        self._state = ControlState()
        self._time = 0.0
        self._integral = [0.0, 0.0, 0.0]
        self._prev_error = [0.0, 0.0, 0.0]

    def step(self, dt: float, inputs: dict[str, Any] | None = None) -> dict[str, Any]:
        inputs = inputs or {}
        if self.fidelity == "Low":
            return self._step_low(dt, inputs)
        elif self.fidelity == "Mid":
            return self._step_mid(dt, inputs)
        elif self.fidelity == "Detail":
            return self._step_detail(dt, inputs)
        return self._step_low(dt, inputs)

    def _step_low(self, dt: float, inputs: dict[str, Any]) -> dict[str, Any]:
        Kp = self._params.get("Kp", [1.0, 1.0, 1.0])
        Ki = self._params.get("Ki", [0.1, 0.1, 0.1])
        Kd = self._params.get("Kd", [0.05, 0.05, 0.05])

        target = inputs.get("target", [0.0, 0.0, 0.0])
        current = inputs.get("current", [0.0, 0.0, 0.0])

        error = [t - c for t, c in zip(target, current)]

        for i in range(3):
            self._integral[i] += error[i] * dt
            max_integral = self._params.get("max_cmd", [25.0, 25.0, 25.0])[i] / max(Ki[i], 0.001)
            self._integral[i] = max(-max_integral, min(max_integral, self._integral[i]))

        derivative = [(error[i] - self._prev_error[i]) / max(dt, 1e-6) for i in range(3)]

        elevator = Kp[0] * error[0] + Ki[0] * self._integral[0] + Kd[0] * derivative[0]
        aileron = Kp[1] * error[1] + Ki[1] * self._integral[1] + Kd[1] * derivative[1]
        rudder = Kp[2] * error[2] + Ki[2] * self._integral[2] + Kd[2] * derivative[2]

        elev_limit = self._params.get("elevator_limit", 25.0)
        ail_limit = self._params.get("aileron_limit", 25.0)
        rud_limit = self._params.get("rudder_limit", 25.0)

        elevator = max(-elev_limit, min(elev_limit, elevator))
        aileron = max(-ail_limit, min(ail_limit, aileron))
        rudder = max(-rud_limit, min(rud_limit, rudder))

        self._prev_error = error[:]
        self._state = ControlState(elevator_cmd=elevator, aileron_cmd=aileron, rudder_cmd=rudder, throttle_cmd=inputs.get("throttle", 0.5))
        self._time += dt

        return ControlOutput(state=self._state, tracking_error=error, fidelity="Low").model_dump()

    def _step_mid(self, dt: float, inputs: dict[str, Any]) -> dict[str, Any]:
        Kp = self._params.get("Kp", [1.0, 1.0, 1.0])
        Ki = self._params.get("Ki", [0.1, 0.1, 0.1])
        Kd = self._params.get("Kd", [0.05, 0.05, 0.05])

        gain_schedule = self._params.get("gain_schedule", {})
        if gain_schedule:
            V = inputs.get("airspeed", 50.0)
            for speed_range, gains in gain_schedule.items():
                lo, hi = speed_range.split("-")
                if float(lo) <= V <= float(hi):
                    Kp = gains.get("Kp", Kp)
                    Ki = gains.get("Ki", Ki)
                    Kd = gains.get("Kd", Kd)
                    break

        target = inputs.get("target", [0.0, 0.0, 0.0])
        current = inputs.get("current", [0.0, 0.0, 0.0])
        error = [t - c for t, c in zip(target, current)]

        for i in range(3):
            self._integral[i] += error[i] * dt
            max_int = 25.0 / max(Ki[i], 0.001)
            self._integral[i] = max(-max_int, min(max_int, self._integral[i]))

        derivative = [(error[i] - self._prev_error[i]) / max(dt, 1e-6) for i in range(3)]

        sas_pitch_gain = self._params.get("sas_pitch_gain", 0.5)
        sas_roll_gain = self._params.get("sas_roll_gain", 0.3)
        sas_yaw_gain = self._params.get("sas_yaw_gain", 0.4)

        p = inputs.get("angular_rates", [0, 0, 0])
        sas_pitch = -sas_pitch_gain * p[1]
        sas_roll = -sas_roll_gain * p[0]
        sas_yaw = -sas_yaw_gain * p[2]

        elevator = Kp[0] * error[0] + Ki[0] * self._integral[0] + Kd[0] * derivative[0] + sas_pitch
        aileron = Kp[1] * error[1] + Ki[1] * self._integral[1] + Kd[1] * derivative[1] + sas_roll
        rudder = Kp[2] * error[2] + Ki[2] * self._integral[2] + Kd[2] * derivative[2] + sas_yaw

        autopilot_mode = inputs.get("autopilot_mode", "OFF")
        throttle = inputs.get("throttle", 0.5)

        if autopilot_mode == "ALTITUDE_HOLD":
            alt_error = inputs.get("target_altitude", 1000.0) - inputs.get("current_altitude", 1000.0)
            throttle = 0.5 + 0.01 * alt_error
            throttle = max(0, min(1, throttle))
        elif autopilot_mode == "HEADING_HOLD":
            hdg_error = inputs.get("target_heading", 0.0) - inputs.get("current_heading", 0.0)
            rudder += 0.1 * hdg_error

        servo_tau = self._params.get("servo_tau", 0.05)
        elev_limit = self._params.get("elevator_limit", 25.0)
        ail_limit = self._params.get("aileron_limit", 25.0)
        rud_limit = self._params.get("rudder_limit", 25.0)

        elevator = max(-elev_limit, min(elev_limit, elevator))
        aileron = max(-ail_limit, min(ail_limit, aileron))
        rudder = max(-rud_limit, min(rud_limit, rudder))

        prev_elev = self._state.elevator_cmd
        prev_ail = self._state.aileron_cmd
        prev_rud = self._state.rudder_cmd

        elev_actual = prev_elev + (elevator - prev_elev) * (1 - math.exp(-dt / servo_tau))
        ail_actual = prev_ail + (aileron - prev_ail) * (1 - math.exp(-dt / servo_tau))
        rud_actual = prev_rud + (rudder - prev_rud) * (1 - math.exp(-dt / servo_tau))

        self._prev_error = error[:]
        self._state = ControlState(elevator_cmd=elev_actual, aileron_cmd=ail_actual, rudder_cmd=rud_actual, throttle_cmd=throttle, autopilot_mode=autopilot_mode)
        self._time += dt

        return ControlOutput(state=self._state, tracking_error=error, fidelity="Mid").model_dump()

    def _step_detail(self, dt: float, inputs: dict[str, Any]) -> dict[str, Any]:
        target = inputs.get("target", [0.0, 0.0, 0.0])
        current = inputs.get("current", [0.0, 0.0, 0.0])
        error = [t - c for t, c in zip(target, current)]

        A = np.array(self._params.get("state_matrix", [[-0.5, 0, 0], [0, -0.3, 0], [0, 0, -0.4]]))
        B = np.array(self._params.get("input_matrix", [[1, 0, 0], [0, 1, 0], [0, 0, 1]]))
        Q_lqr = np.array(self._params.get("lqr_Q", np.eye(3)))
        R_lqr = np.array(self._params.get("lqr_R", np.eye(3)))

        try:
            from scipy.linalg import solve_continuous_are
            P = solve_continuous_are(A, B, Q_lqr, R_lqr)
            K = np.linalg.inv(R_lqr) @ B.T @ P
            use_lqr = True
        except Exception:
            Kp = self._params.get("Kp", [1.0, 1.0, 1.0])
            K = np.diag(Kp)
            use_lqr = False

        x = np.array(current)
        u_cmd = -K @ x

        sas_pitch_gain = self._params.get("sas_pitch_gain", 0.5)
        sas_roll_gain = self._params.get("sas_roll_gain", 0.3)
        sas_yaw_gain = self._params.get("sas_yaw_gain", 0.4)
        p = inputs.get("angular_rates", [0, 0, 0])
        u_cmd[0] += -sas_pitch_gain * p[1]
        u_cmd[1] += -sas_roll_gain * p[0]
        u_cmd[2] += -sas_yaw_gain * p[2]

        V = inputs.get("airspeed", 50.0)
        V_D = self._params.get("V_D", 120.0)
        n_max = self._params.get("n_max", 3.5)
        n_min = self._params.get("n_min", -1.0)
        n_current = inputs.get("load_factor", 1.0)

        if V > V_D * 0.95:
            u_cmd[0] = min(u_cmd[0], 0)
        if n_current > n_max * 0.9:
            u_cmd[0] = min(u_cmd[0], 0)
        if n_current < n_min * 0.9:
            u_cmd[0] = max(u_cmd[0], 0)

        elevator = float(u_cmd[0])
        aileron = float(u_cmd[1])
        rudder = float(u_cmd[2])

        elev_limit = self._params.get("elevator_limit", 25.0)
        ail_limit = self._params.get("aileron_limit", 25.0)
        rud_limit = self._params.get("rudder_limit", 25.0)
        elevator = max(-elev_limit, min(elev_limit, elevator))
        aileron = max(-ail_limit, min(ail_limit, aileron))
        rudder = max(-rud_limit, min(rud_limit, rudder))

        servo_omega_n = self._params.get("servo_omega_n", 50.0)
        servo_zeta = self._params.get("servo_zeta", 0.7)
        servo_rate_limit = self._params.get("servo_rate_limit", 60.0)

        prev_elev = self._state.elevator_cmd
        prev_ail = self._state.aileron_cmd
        prev_rud = self._state.rudder_cmd

        def servo_2nd_order(cmd, prev, dt):
            error = cmd - prev
            accel = servo_omega_n ** 2 * error - 2 * servo_zeta * servo_omega_n * 0
            rate = max(-servo_rate_limit, min(servo_rate_limit, accel * dt))
            return prev + rate * dt

        elev_actual = servo_2nd_order(elevator, prev_elev, dt)
        ail_actual = servo_2nd_order(aileron, prev_ail, dt)
        rud_actual = servo_2nd_order(rudder, prev_rud, dt)

        autopilot_mode = inputs.get("autopilot_mode", "OFF")
        throttle = inputs.get("throttle", 0.5)

        self._state = ControlState(elevator_cmd=elev_actual, aileron_cmd=ail_actual, rudder_cmd=rud_actual, throttle_cmd=throttle, autopilot_mode=autopilot_mode)
        self._time += dt

        result = ControlOutput(state=self._state, tracking_error=error, fidelity="Detail").model_dump()
        result["lqr_active"] = use_lqr
        result["envelope_protection_active"] = V > V_D * 0.95 or abs(n_current) > abs(n_max) * 0.9
        return result

    def get_state(self) -> dict[str, Any]:
        return self._state.model_dump()

    def reset(self) -> None:
        self._state = ControlState()
        self._time = 0.0
        self._integral = [0.0, 0.0, 0.0]
        self._prev_error = [0.0, 0.0, 0.0]

    def get_supported_fidelities(self) -> list[str]:
        return ["Low", "Mid", "Detail"]

    def get_schema_references(self) -> list[str]:
        return ["AircraftAvionics", "AircraftFlightEnvelope"]