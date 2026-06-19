from __future__ import annotations

import math
from typing import Any

from src.domain.plugins.interfaces import BatteryOutput, BatteryState, IPhysicsModelPlugin


class BatteryModel(IPhysicsModelPlugin):

    def __init__(self, fidelity: str = "Low"):
        self.fidelity = fidelity
        self._state = BatteryState()
        self._time = 0.0
        self._params: dict[str, Any] = {}
        self._energy_consumed = 0.0

    def initialize(self, params: dict[str, Any]) -> None:
        self._params = params
        self._state = BatteryState(
            soc=params.get("initial_soc", 1.0),
            soh=params.get("initial_soh", 1.0),
            terminal_voltage=params.get("battery_voltage", 48.0),
            current=0.0,
            temperature=params.get("initial_temperature", 25.0),
            v_rc1=0.0,
            v_rc2=0.0,
        )
        self._time = 0.0
        self._energy_consumed = 0.0

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
        Q_nom = self._params.get("battery_capacity", 50.0)
        V_nom = self._params.get("battery_voltage", 48.0)
        R0 = self._params.get("R0", 0.02)
        I = inputs.get("current", 0.0)

        OCV = V_nom
        V_terminal = OCV - I * R0

        self._state.soc -= (I * dt) / (Q_nom * 3600)
        self._state.soc = max(0.0, min(1.0, self._state.soc))
        self._state.terminal_voltage = V_terminal
        self._state.current = I
        self._energy_consumed += abs(V_terminal * I * dt / 3600)

        self._time += dt
        return BatteryOutput(state=self._state, power=V_terminal * I, energy_consumed=self._energy_consumed, fidelity="Low").model_dump()

    def _step_mid(self, dt: float, inputs: dict[str, Any]) -> dict[str, Any]:
        Q_nom = self._params.get("battery_capacity", 50.0)
        V_nom = self._params.get("battery_voltage", 48.0)
        R0 = self._params.get("R0", 0.02)
        R1 = self._params.get("R1", 0.01)
        tau1 = self._params.get("tau1", 10.0)
        I = inputs.get("current", 0.0)

        OCV = self._ocv_from_soc(self._state.soc)

        v_rc1_new = self._state.v_rc1 * math.exp(-dt / tau1) + R1 * I * (1 - math.exp(-dt / tau1))

        V_terminal = OCV - I * R0 - v_rc1_new

        self._state.soc -= (I * dt) / (Q_nom * 3600)
        self._state.soc = max(0.0, min(1.0, self._state.soc))

        if abs(I) < 0.1 and self._time > 60:
            ocv_measured = V_terminal + I * R0
            soc_from_ocv = self._soc_from_ocv(ocv_measured)
            if soc_from_ocv is not None:
                self._state.soc = 0.7 * self._state.soc + 0.3 * soc_from_ocv

        self._state.soh = self._params.get("initial_soh", 1.0) - self._params.get("degradation_rate", 0.0001) * self._time / 3600
        self._state.soh = max(0.0, min(1.0, self._state.soh))

        m_cell = self._params.get("cell_mass", 5.0)
        Cp = self._params.get("cell_Cp", 1000.0)
        h = self._params.get("cooling_coeff", 10.0)
        A_cool = self._params.get("cooling_area", 0.1)
        T_amb = inputs.get("ambient_temperature", 25.0)
        Q_gen = I ** 2 * (R0 + R1)
        Q_cool = h * A_cool * (self._state.temperature - T_amb)
        dT = (Q_gen - Q_cool) / (m_cell * Cp) * dt
        self._state.temperature += dT

        self._state.terminal_voltage = V_terminal
        self._state.current = I
        self._state.v_rc1 = v_rc1_new
        self._energy_consumed += abs(V_terminal * I * dt / 3600)
        self._time += dt

        return BatteryOutput(state=self._state, power=V_terminal * I, energy_consumed=self._energy_consumed, fidelity="Mid").model_dump()

    def _step_detail(self, dt: float, inputs: dict[str, Any]) -> dict[str, Any]:
        Q_nom = self._params.get("battery_capacity", 50.0)
        V_nom = self._params.get("battery_voltage", 48.0)
        R0 = self._params.get("R0", 0.02)
        R1 = self._params.get("R1", 0.01)
        R2 = self._params.get("R2", 0.005)
        tau1 = self._params.get("tau1", 10.0)
        tau2 = self._params.get("tau2", 100.0)
        I = inputs.get("current", 0.0)

        OCV = self._ocv_from_soc(self._state.soc)

        v_rc1_new = self._state.v_rc1 * math.exp(-dt / tau1) + R1 * I * (1 - math.exp(-dt / tau1))
        v_rc2_new = self._state.v_rc2 * math.exp(-dt / tau2) + R2 * I * (1 - math.exp(-dt / tau2))

        V_terminal = OCV - I * R0 - v_rc1_new - v_rc2_new

        self._state.soc -= (I * dt) / (Q_nom * 3600)
        self._state.soc = max(0.0, min(1.0, self._state.soc))

        P_matrix = self._params.get("ekf_P", [[0.01, 0], [0, 0.01]])
        Q_ekf = self._params.get("ekf_Q", [[0.001, 0], [0, 0.0001]])
        R_ekf = self._params.get("ekf_R", 0.01)

        x_pred = [self._state.soc, v_rc1_new]
        P_pred = [[P_matrix[0][0] + Q_ekf[0][0], P_matrix[0][1]], [P_matrix[1][0], P_matrix[1][1] + Q_ekf[1][1]]]

        h_pred = self._ocv_from_soc(x_pred[0]) - I * R0 - x_pred[1]
        innovation = V_terminal - h_pred
        H = [self._ocv_derivative(x_pred[0]), -1]
        S = H[0] * P_pred[0][0] * H[0] + H[1] * P_pred[1][0] * H[0] + H[0] * P_pred[0][1] * H[1] + H[1] * P_pred[1][1] * H[1] + R_ekf

        if abs(S) > 1e-10:
            K = [(P_pred[0][0] * H[0] + P_pred[0][1] * H[1]) / S, (P_pred[1][0] * H[0] + P_pred[1][1] * H[1]) / S]
            x_upd = [x_pred[0] + K[0] * innovation, x_pred[1] + K[1] * innovation]
            self._state.soc = max(0.0, min(1.0, x_upd[0]))
            v_rc1_new = x_upd[1]

        A_cal = self._params.get("calendar_aging_A", 1e-4)
        Ea = self._params.get("calendar_aging_Ea", 50000.0)
        R_gas = 8.314
        T_K = self._state.temperature + 273.15
        delta_Q_cal = A_cal * math.exp(-Ea / (R_gas * T_K)) * math.sqrt(self._time / 3600)

        B_cyc = self._params.get("cycle_aging_B", 1e-5)
        z_cyc = self._params.get("cycle_aging_z", 0.5)
        DOD = abs(I * dt / (Q_nom * 3600))
        N_equiv = self._time / 3600
        delta_Q_cyc = B_cyc * (DOD ** z_cyc) * math.sqrt(max(N_equiv, 0))

        self._state.soh = max(0.0, min(1.0, 1.0 - delta_Q_cal - delta_Q_cyc))

        m_cell = self._params.get("cell_mass", 5.0)
        Cp = self._params.get("cell_Cp", 1000.0)
        h = self._params.get("cooling_coeff", 10.0)
        A_cool = self._params.get("cooling_area", 0.1)
        T_amb = inputs.get("ambient_temperature", 25.0)
        Q_gen = I ** 2 * R0 + I * v_rc1_new + I * v_rc2_new
        Q_cool = h * A_cool * (self._state.temperature - T_amb)
        dT = (Q_gen - Q_cool) / (m_cell * Cp) * dt
        self._state.temperature += dT

        self._state.terminal_voltage = V_terminal
        self._state.current = I
        self._state.v_rc1 = v_rc1_new
        self._state.v_rc2 = v_rc2_new
        self._energy_consumed += abs(V_terminal * I * dt / 3600)
        self._time += dt

        low_soc_event = None
        if self._state.soc < self._params.get("low_soc_threshold", 0.2):
            low_soc_event = {"event_type": "aeroforge.battery.low_soc", "soc": self._state.soc}

        result = BatteryOutput(state=self._state, power=V_terminal * I, energy_consumed=self._energy_consumed, fidelity="Detail").model_dump()
        if low_soc_event:
            result["low_soc_event"] = low_soc_event
        return result

    def get_state(self) -> dict[str, Any]:
        return self._state.model_dump()

    def reset(self) -> None:
        self._state = BatteryState()
        self._time = 0.0
        self._energy_consumed = 0.0

    def get_supported_fidelities(self) -> list[str]:
        return ["Low", "Mid", "Detail"]

    def get_schema_references(self) -> list[str]:
        return ["AircraftPropulsion"]

    def _ocv_from_soc(self, soc: float) -> float:
        V_nom = self._params.get("battery_voltage", 48.0)
        return V_nom * (0.9 + 0.1 * soc)

    def _soc_from_ocv(self, ocv: float) -> float | None:
        V_nom = self._params.get("battery_voltage", 48.0)
        if V_nom <= 0:
            return None
        soc = (ocv / V_nom - 0.9) / 0.1
        return max(0.0, min(1.0, soc))

    def _ocv_derivative(self, soc: float) -> float:
        V_nom = self._params.get("battery_voltage", 48.0)
        return 0.1 * V_nom