from __future__ import annotations

import math
import warnings
from typing import Any, TYPE_CHECKING

import numpy as np

from src.domain.plugins.interfaces import (
    DOF6Output, DOF6State, IPhysicsModelPlugin, StabilityCheck,
)

if TYPE_CHECKING:
    from src.domain.plugins.aerodynamic_database import AerodynamicDatabase


class DOF6Model(IPhysicsModelPlugin):

    def __init__(self, fidelity: str = "Low"):
        self.fidelity = fidelity
        self._state = DOF6State()
        self._time = 0.0
        self._params: dict[str, Any] = {}
        self._aero_database_ref: AerodynamicDatabase | None = None

    def initialize(self, params: dict[str, Any]) -> None:
        self._params = params
        self._state = DOF6State(
            position=[0.0, 0.0, params.get("initial_altitude", 1000.0)],
            velocity=[params.get("initial_speed", 50.0), 0.0, 0.0],
            attitude=[0.0, 0.0, 0.0],
            angular_rates=[0.0, 0.0, 0.0],
        )
        self._time = 0.0
        aero_db = params.get("aero_database_ref")
        if aero_db is not None:
            self._aero_database_ref = aero_db

    def step(self, dt: float, inputs: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.fidelity == "Low":
            return self._step_low(dt, inputs or {})
        elif self.fidelity == "Mid":
            return self._step_mid(dt, inputs or {})
        elif self.fidelity == "Detail":
            return self._step_detail(dt, inputs or {})
        return self._step_low(dt, inputs or {})

    def _step_low(self, dt: float, inputs: dict[str, Any]) -> dict[str, Any]:
        m = self._params.get("mass", 1500.0)
        S = self._params.get("wing_area", 16.0)
        V = max(math.sqrt(sum(v ** 2 for v in self._state.velocity)), 1.0)
        rho = self._isa_density(self._state.position[2])
        q_s = 0.5 * rho * V ** 2 * S

        alpha = self._compute_alpha()
        CL_alpha = self._params.get("CL_alpha", 5.0)
        CD_0 = self._params.get("CD_0", 0.02)
        k = self._params.get("k_induced", 0.05)

        CL = CL_alpha * alpha
        CD = CD_0 + k * CL ** 2

        elevator = inputs.get("elevator_cmd", 0.0)
        CL += elevator * 0.01

        L = q_s * CL
        D = q_s * CD
        T = inputs.get("thrust", self._params.get("max_thrust", 5000.0))

        phi, theta, psi = self._state.attitude
        u, v, w = self._state.velocity
        p, q, r = self._state.angular_rates

        du = (T * math.cos(alpha) - D) / m - q * w + r * v
        dv = 0.0 - r * u + p * w
        dw = (-T * math.sin(alpha) + L - m * 9.81 * math.cos(theta)) / m - p * v + q * u

        u_new = u + du * dt
        v_new = v + dv * dt
        w_new = w + dw * dt

        x_new = self._state.position[0] + u_new * dt
        y_new = self._state.position[1] + v_new * dt
        z_new = self._state.position[2] - w_new * dt

        self._state = DOF6State(
            position=[x_new, y_new, z_new],
            velocity=[u_new, v_new, w_new],
            attitude=self._state.attitude,
            angular_rates=self._state.angular_rates,
            acceleration=[du, dv, dw],
        )
        self._time += dt

        return DOF6Output(
            state=self._state,
            forces=[T * math.cos(alpha) - D, 0, -T * math.sin(alpha) + L],
            moments=[0.0, 0.0, 0.0],
            fidelity="Low",
        ).model_dump()

    def _step_mid(self, dt: float, inputs: dict[str, Any]) -> dict[str, Any]:
        m = self._params.get("mass", 1500.0)
        Ixx = self._params.get("Ixx", 1000.0)
        Iyy = self._params.get("Iyy", 3000.0)
        Izz = self._params.get("Izz", 3500.0)
        Ixz = self._params.get("Ixz", 50.0)
        S = self._params.get("wing_area", 16.0)
        b = self._params.get("wingspan", 10.0)
        c = self._params.get("chord_length", 1.6)

        V = max(math.sqrt(sum(v ** 2 for v in self._state.velocity)), 1.0)
        rho = self._isa_density(self._state.position[2])
        q_s = 0.5 * rho * V ** 2 * S

        alpha = self._compute_alpha()
        beta = self._compute_beta()

        CL = self._interp_1d(alpha, self._params.get("CL_table", [(0, 0.3), (0.1, 0.8), (0.2, 1.3)]))
        CD = self._interp_1d(alpha, self._params.get("CD_table", [(0, 0.02), (0.1, 0.04), (0.2, 0.08)]))
        Cm = self._interp_1d(alpha, self._params.get("Cm_table", [(0, 0.0), (0.1, -0.05), (0.2, -0.1)]))

        elevator = inputs.get("elevator_cmd", 0.0)
        aileron = inputs.get("aileron_cmd", 0.0)
        rudder = inputs.get("rudder_cmd", 0.0)

        CL += elevator * 0.005
        CY = -0.3 * beta + rudder * 0.01
        Cl = -0.1 * beta + aileron * 0.005
        Cn = 0.1 * beta - rudder * 0.005

        phi, theta, psi = self._state.attitude
        u, v, w = self._state.velocity
        p, q, r = self._state.angular_rates

        Fx = q_s * (-CD * math.cos(alpha) + CL * math.sin(alpha)) + inputs.get("thrust", self._params.get("max_thrust", 5000.0))
        Fy = q_s * CY
        Fz = q_s * (-CD * math.sin(alpha) - CL * math.cos(alpha)) + m * 9.81

        du = Fx / m - q * w + r * v - 9.81 * math.sin(theta)
        dv = Fy / m - r * u + p * w + 9.81 * math.sin(phi) * math.cos(theta)
        dw = Fz / m - p * v + q * u - 9.81 * math.cos(phi) * math.cos(theta)

        Mx = q_s * b * Cl
        My = q_s * c * Cm
        Mz = q_s * b * Cn

        Gamma = Ixx * Izz - Ixz ** 2
        dp = (Izz * Mx + Ixz * Mz - (Izz * (Izz - Iyy) + Ixz ** 2) * q * r + Ixz * (Ixx - Iyy + Izz) * p * q) / Gamma
        dq = (My - (Ixx - Izz) * p * r - Ixz * (p ** 2 - r ** 2)) / Iyy
        dr = (Ixx * Mz + Ixz * Mx + (Ixx * (Ixx - Iyy) + Ixz ** 2) * p * q - Ixz * (Izz - Iyy + Ixx) * q * r) / Gamma

        def rk4_derivs(state_vec, t):
            return np.array([du, dv, dw, dp, dq, dr])

        state_vec = np.array([u, v, w, p, q, r])
        k1 = rk4_derivs(state_vec, self._time)
        k2 = rk4_derivs(state_vec + 0.5 * dt * k1, self._time + 0.5 * dt)
        k3 = rk4_derivs(state_vec + 0.5 * dt * k2, self._time + 0.5 * dt)
        k4 = rk4_derivs(state_vec + dt * k3, self._time + dt)
        new_vec = state_vec + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)

        u_new, v_new, w_new = new_vec[0], new_vec[1], new_vec[2]
        p_new, q_new, r_new = new_vec[3], new_vec[4], new_vec[5]

        phi_new = phi + (p_new + (q_new * math.sin(phi) + r_new * math.cos(phi)) * math.tan(theta)) * dt
        theta_new = theta + (q_new * math.cos(phi) - r_new * math.sin(phi)) * dt
        psi_new = psi + (q_new * math.sin(phi) + r_new * math.cos(phi)) / max(math.cos(theta), 0.01) * dt

        if abs(theta_new) > math.radians(85):
            theta_new = math.copysign(math.radians(85), theta_new)

        x_new = self._state.position[0] + u_new * dt
        y_new = self._state.position[1] + v_new * dt
        z_new = self._state.position[2] - w_new * dt

        self._state = DOF6State(
            position=[x_new, y_new, z_new],
            velocity=[u_new, v_new, w_new],
            attitude=[phi_new, theta_new, psi_new],
            angular_rates=[p_new, q_new, r_new],
            acceleration=[du, dv, dw],
        )
        self._time += dt

        return DOF6Output(state=self._state, forces=[Fx, Fy, Fz], moments=[Mx, My, Mz], fidelity="Mid").model_dump()

    def _step_detail(self, dt: float, inputs: dict[str, Any]) -> dict[str, Any]:
        m = self._params.get("mass", 1500.0)
        Ixx = self._params.get("Ixx", 1000.0)
        Iyy = self._params.get("Iyy", 3000.0)
        Izz = self._params.get("Izz", 3500.0)
        Ixz = self._params.get("Ixz", 50.0)
        S = self._params.get("wing_area", 16.0)
        b = self._params.get("wingspan", 10.0)
        c = self._params.get("chord_length", 1.6)

        V = max(math.sqrt(sum(v ** 2 for v in self._state.velocity)), 1.0)
        rho = self._isa_density(self._state.position[2])
        q_s = 0.5 * rho * V ** 2 * S

        alpha = self._compute_alpha()
        beta = self._compute_beta()
        mach = V / self._speed_of_sound(self._state.position[2])
        reynolds = rho * V * c / self._dynamic_viscosity(self._state.position[2])

        elevator = inputs.get("elevator_cmd", 0.0)
        aileron = inputs.get("aileron_cmd", 0.0)
        rudder = inputs.get("rudder_cmd", 0.0)

        if self._aero_database_ref is not None:
            CL, CD, CY, Cm, Cl, Cn = self._query_aero_database(
                alpha, beta, mach, reynolds, elevator, aileron, rudder
            )
        else:
            p_hat = self._state.angular_rates[0] * b / (2 * V)
            q_hat = self._state.angular_rates[1] * c / (2 * V)
            r_hat = self._state.angular_rates[2] * b / (2 * V)

            CL = self._interp_2d(alpha, elevator, self._params.get("CL_2d", {}))
            CD = self._interp_2d(alpha, elevator, self._params.get("CD_2d", {}))
            CY = self._interp_1d(alpha, self._params.get("CY_table", [(0, 0), (0.1, -0.03)]))
            Cm = self._interp_2d(alpha, elevator, self._params.get("Cm_2d", {}))
            Cl = self._interp_1d(beta, self._params.get("Cl_table", [(0, 0), (0.1, -0.05)]))
            Cn = self._interp_1d(beta, self._params.get("Cn_table", [(0, 0), (0.1, 0.03)]))

            CL += elevator * 0.005
            CY += rudder * 0.01
            Cl += aileron * 0.005
            Cn -= rudder * 0.008
            Cm += q_hat * self._params.get("Cmq", -15.0)
            Cn += r_hat * self._params.get("Cnr", -0.2)

        q0, q1, q2, q3 = self._get_quaternion()
        phi, theta, psi = self._state.attitude
        u, v, w = self._state.velocity
        p, q, r = self._state.angular_rates

        Fx = q_s * (-CD * math.cos(alpha) + CL * math.sin(alpha)) + inputs.get("thrust", self._params.get("max_thrust", 5000.0))
        Fy = q_s * CY
        Fz = q_s * (-CD * math.sin(alpha) - CL * math.cos(alpha)) + m * 9.81

        du = Fx / m - q * w + r * v - 9.81 * math.sin(theta)
        dv = Fy / m - r * u + p * w + 9.81 * math.sin(phi) * math.cos(theta)
        dw = Fz / m - p * v + q * u - 9.81 * math.cos(phi) * math.cos(theta)

        Mx = q_s * b * Cl
        My = q_s * c * Cm
        Mz = q_s * b * Cn

        Gamma = Ixx * Izz - Ixz ** 2
        dp = (Izz * Mx + Ixz * Mz - (Izz * (Izz - Iyy) + Ixz ** 2) * q * r + Ixz * (Ixx - Iyy + Izz) * p * q) / Gamma
        dq = (My - (Ixx - Izz) * p * r - Ixz * (p ** 2 - r ** 2)) / Iyy
        dr = (Ixx * Mz + Ixz * Mx + (Ixx * (Ixx - Iyy) + Ixz ** 2) * p * q - Ixz * (Izz - Iyy + Ixx) * q * r) / Gamma

        state_vec = np.array([u, v, w, p, q, r])
        derivs = np.array([du, dv, dw, dp, dq, dr])

        k1 = derivs
        s2 = state_vec + 0.5 * dt * k1
        k2 = derivs
        s3 = state_vec + 0.5 * dt * k2
        k3 = derivs
        s4 = state_vec + dt * k3
        k4 = derivs
        new_vec = state_vec + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)

        u_new, v_new, w_new = new_vec[0], new_vec[1], new_vec[2]
        p_new, q_new, r_new = new_vec[3], new_vec[4], new_vec[5]

        omega = np.array([p_new, q_new, r_new])
        Omega = np.array([
            [0, -omega[0], -omega[1], -omega[2]],
            [omega[0], 0, omega[2], -omega[1]],
            [omega[1], -omega[2], 0, omega[0]],
            [omega[2], omega[1], -omega[0], 0],
        ])
        q_vec = np.array([q0, q1, q2, q3])
        q_dot = 0.5 * Omega @ q_vec
        q_new = q_vec + q_dot * dt
        q_norm = np.linalg.norm(q_new)
        if q_norm > 0:
            q_new = q_new / q_norm

        phi_new = math.atan2(2 * (q_new[0] * q_new[1] + q_new[2] * q_new[3]), 1 - 2 * (q_new[1] ** 2 + q_new[2] ** 2))
        theta_new = math.asin(max(-1, min(1, 2 * (q_new[0] * q_new[2] - q_new[3] * q_new[1]))))
        psi_new = math.atan2(2 * (q_new[0] * q_new[3] + q_new[1] * q_new[2]), 1 - 2 * (q_new[2] ** 2 + q_new[3] ** 2))

        x_new = self._state.position[0] + u_new * dt
        y_new = self._state.position[1] + v_new * dt
        z_new = self._state.position[2] - w_new * dt

        self._state = DOF6State(
            position=[x_new, y_new, z_new],
            velocity=[u_new, v_new, w_new],
            attitude=[phi_new, theta_new, psi_new],
            angular_rates=[p_new, q_new, r_new],
            acceleration=[du, dv, dw],
        )
        self._time += dt

        return DOF6Output(state=self._state, forces=[Fx, Fy, Fz], moments=[Mx, My, Mz], fidelity="Detail").model_dump()

    def get_state(self) -> dict[str, Any]:
        return self._state.model_dump()

    def reset(self) -> None:
        self._state = DOF6State()
        self._time = 0.0

    def get_supported_fidelities(self) -> list[str]:
        return ["Low", "Mid", "Detail"]

    def get_schema_references(self) -> list[str]:
        return ["AircraftGeometry", "AircraftPropulsion"]

    def validate_numerical_stability(self) -> StabilityCheck:
        V = math.sqrt(sum(v ** 2 for v in self._state.velocity))
        if V > 1000 or math.isnan(V):
            return StabilityCheck(is_stable=False, divergence_step=0, residual=V, message="Velocity divergence detected")
        for a in self._state.attitude:
            if math.isnan(a):
                return StabilityCheck(is_stable=False, divergence_step=0, residual=0, message="Attitude NaN detected")
        return StabilityCheck(is_stable=True, residual=0, message="Stable")

    def _compute_alpha(self) -> float:
        u, v, w = self._state.velocity
        return math.atan2(w, max(u, 0.1))

    def _compute_beta(self) -> float:
        u, v, w = self._state.velocity
        V = math.sqrt(u ** 2 + v ** 2 + w ** 2)
        if V < 0.1:
            return 0.0
        return math.asin(max(-1, min(1, v / V)))

    def _isa_density(self, altitude: float) -> float:
        T0 = 288.15
        P0 = 101325.0
        L = 0.0065
        g = 9.80665
        R = 287.058
        if altitude < 11000:
            T = T0 - L * altitude
            P = P0 * (T / T0) ** (g / (L * R))
        else:
            T11 = T0 - L * 11000
            P11 = P0 * (T11 / T0) ** (g / (L * R))
            T = T11
            P = P11 * math.exp(-g * (altitude - 11000) / (R * T11))
        return P / (R * T)

    def _query_aero_database(
        self, alpha: float, beta: float, mach: float, reynolds: float,
        elevator: float, aileron: float, rudder: float,
    ) -> tuple[float, float, float, float, float, float]:
        if self._aero_database_ref is None:
            return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        coeffs = self._aero_database_ref.query_coefficients(alpha, beta, mach, reynolds)

        if coeffs.is_extrapolated:
            warnings.warn(
                f"6DOF Detail: Aero database extrapolation at alpha={math.degrees(alpha):.1f}°, "
                f"beta={math.degrees(beta):.1f}°, M={mach:.3f}, Re={reynolds:.2e}",
                stacklevel=2,
            )

        CL = coeffs.CL + elevator * 0.005
        CD = coeffs.CD
        CY = coeffs.CY + rudder * 0.01
        Cm = coeffs.CM
        Cl = coeffs.Cl + aileron * 0.005
        Cn = coeffs.Cn - rudder * 0.008

        return (CL, CD, CY, Cm, Cl, Cn)

    @staticmethod
    def _speed_of_sound(altitude: float) -> float:
        T0 = 288.15
        L = 0.0065
        if altitude < 11000:
            T = T0 - L * max(altitude, 0.0)
        else:
            T = T0 - L * 11000.0
        return math.sqrt(1.4 * 287.058 * T)

    @staticmethod
    def _dynamic_viscosity(altitude: float) -> float:
        T0 = 288.15
        L = 0.0065
        if altitude < 11000:
            T = T0 - L * max(altitude, 0.0)
        else:
            T = T0 - L * 11000.0
        mu0 = 1.716e-5
        T_ref = 273.15 + 110.0
        S = 110.4
        return mu0 * (T / T_ref) ** 1.5 * (T_ref + S) / (T + S)

    def _interp_1d(self, x: float, table: list | dict) -> float:
        if isinstance(table, dict):
            table = list(table.items())
        if not table:
            return 0.0
        sorted_table = sorted(table, key=lambda t: t[0])
        if x <= sorted_table[0][0]:
            return sorted_table[0][1]
        if x >= sorted_table[-1][0]:
            return sorted_table[-1][1]
        for i in range(len(sorted_table) - 1):
            x0, y0 = sorted_table[i]
            x1, y1 = sorted_table[i + 1]
            if x0 <= x <= x1:
                t = (x - x0) / (x1 - x0) if x1 != x0 else 0
                return y0 + t * (y1 - y0)
        return 0.0

    def _interp_2d(self, x: float, y: float, table: dict) -> float:
        if not table:
            return self._interp_1d(x, [])
        x_keys = sorted(table.keys())
        if not x_keys:
            return 0.0
        if x <= x_keys[0]:
            y_table = table[x_keys[0]]
        elif x >= x_keys[-1]:
            y_table = table[x_keys[-1]]
        else:
            for i in range(len(x_keys) - 1):
                if x_keys[i] <= x <= x_keys[i + 1]:
                    t = (x - x_keys[i]) / (x_keys[i + 1] - x_keys[i]) if x_keys[i + 1] != x_keys[i] else 0
                    y_table_low = table[x_keys[i]]
                    y_table_high = table[x_keys[i + 1]]
                    v_low = self._interp_1d(y, y_table_low) if isinstance(y_table_low, list) else y_table_low
                    v_high = self._interp_1d(y, y_table_high) if isinstance(y_table_high, list) else y_table_high
                    return v_low + t * (v_high - v_low)
            y_table = table[x_keys[-1]]
        if isinstance(y_table, list):
            return self._interp_1d(y, y_table)
        return float(y_table) if isinstance(y_table, (int, float)) else 0.0

    def _get_quaternion(self) -> list[float]:
        phi, theta, psi = self._state.attitude
        cr = math.cos(phi / 2)
        sr = math.sin(phi / 2)
        cp = math.cos(theta / 2)
        sp = math.sin(theta / 2)
        cy = math.cos(psi / 2)
        sy = math.sin(psi / 2)
        q0 = cr * cp * cy + sr * sp * sy
        q1 = sr * cp * cy - cr * sp * sy
        q2 = cr * sp * cy + sr * cp * sy
        q3 = cr * cp * sy - sr * sp * cy
        return [q0, q1, q2, q3]