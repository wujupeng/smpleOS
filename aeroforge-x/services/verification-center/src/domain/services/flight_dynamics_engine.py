from __future__ import annotations

import math
from typing import Any

from src.domain.entities.flight_dynamics_analysis import (
    FlightDynamicsAnalysis,
    TrimResult,
    SimulationState,
    DynamicResponseResult,
)


class FlightDynamicsEngine:
    def perform_trim_analysis(self, config: dict[str, Any], trim_type: str = "cruise") -> TrimResult:
        weight_n = float(config.get("mtow_kg", 25)) * 9.81
        wing_area = float(config.get("wing_area_m2", 0.5))
        cruise_speed = float(config.get("cruise_speed_ms", 30))
        cl_max = 1.5

        required_cl = (2 * weight_n) / (1.225 * cruise_speed ** 2 * wing_area) if cruise_speed > 0 else 0
        alpha_trim = required_cl / (2 * math.pi) * 57.3

        elevator_deflection = -alpha_trim * 0.3
        throttle = 0.5 + (cruise_speed / 100.0) * 0.3

        converged = abs(required_cl) < cl_max
        iteration_count = 5 if converged else 20

        return TrimResult(
            trim_type=trim_type,
            alpha_deg=round(alpha_trim, 2),
            elevator_deflection_deg=round(elevator_deflection, 2),
            throttle_pct=round(min(throttle * 100, 100), 1),
            converged=converged,
            iteration_count=iteration_count,
        )

    def run_6dof_simulation(self, config: dict[str, Any], duration_s: float = 10.0, dt: float = 0.02) -> list[SimulationState]:
        states: list[SimulationState] = []
        mass = float(config.get("mtow_kg", 25))
        wing_area = float(config.get("wing_area_m2", 0.5))
        v0 = float(config.get("cruise_speed_ms", 30))
        ixx = mass * 0.02
        iyy = mass * 0.04
        izz = mass * 0.05

        phi, theta, psi = 0.0, 0.0, 0.0
        p, q, r = 0.0, 0.0, 0.0
        u, v, w = v0, 0.0, 0.0

        steps = int(duration_s / dt)
        for i in range(steps):
            t = i * dt
            la = 1.225 * v0 ** 2 * wing_area / 2
            lp = -0.5 * la * 0.1 / ixx if ixx > 0 else 0
            lq = -0.5 * la * 0.2 / iyy if iyy > 0 else 0
            lr = -0.5 * la * 0.15 / izz if izz > 0 else 0

            p += lp * p * dt
            q += lq * q * dt
            r += lr * r * dt

            phi += p * dt
            theta += q * dt
            psi += r * dt

            if i % max(1, steps // 100) == 0:
                states.append(SimulationState(
                    time_s=round(t, 4),
                    phi_deg=round(phi * 57.3, 2),
                    theta_deg=round(theta * 57.3, 2),
                    psi_deg=round(psi * 57.3, 2),
                    p_deg_s=round(p * 57.3, 2),
                    q_deg_s=round(q * 57.3, 2),
                    r_deg_s=round(r * 57.3, 2),
                    u_m_s=round(u, 2),
                    v_m_s=round(v, 2),
                    w_m_s=round(w, 2),
                ))

            if abs(phi) > math.pi or abs(theta) > math.pi / 2:
                break

        return states

    def analyze_dynamic_response(self, config: dict[str, Any], response_type: str = "step") -> DynamicResponseResult:
        mass = float(config.get("mtow_kg", 25))
        wing_area = float(config.get("wing_area_m2", 0.5))
        v0 = float(config.get("cruise_speed_ms", 30))

        q_dyn = 0.5 * 1.225 * v0 ** 2
        c_hat = 2 * mass / (1.225 * v0 * wing_area) if 1.225 * v0 * wing_area > 0 else 1

        omega_sp = 2 * math.pi * 1.5
        zeta_sp = 0.5
        omega_ph = 2 * math.pi * 0.15
        zeta_ph = 0.1

        modes = [
            {"name": "short_period", "frequency_hz": round(omega_sp / (2 * math.pi), 3), "damping_ratio": round(zeta_sp, 4)},
            {"name": "phugoid", "frequency_hz": round(omega_ph / (2 * math.pi), 3), "damping_ratio": round(zeta_ph, 4)},
        ]

        settling_time = 4.0 / (zeta_sp * omega_sp) if zeta_sp * omega_sp > 0 else 10.0
        rise_time = 1.8 / omega_sp if omega_sp > 0 else 5.0
        overshoot = math.exp(-math.pi * zeta_sp / math.sqrt(1 - zeta_sp ** 2)) * 100 if zeta_sp < 1 else 0

        return DynamicResponseResult(
            response_type=response_type,
            settling_time_s=round(settling_time, 3),
            rise_time_s=round(rise_time, 3),
            overshoot_pct=round(overshoot, 1),
            natural_frequency_hz=round(omega_sp / (2 * math.pi), 3),
            damping_ratio=round(zeta_sp, 4),
            modes=modes,
        )

    def run_full_analysis(self, config: dict[str, Any]) -> FlightDynamicsAnalysis:
        analysis = FlightDynamicsAnalysis(aircraft_config=config, status="running")
        trim = self.perform_trim_analysis(config, "cruise")
        analysis.trim_results = [trim]
        analysis.trim_converged = trim.converged

        sim_states = self.run_6dof_simulation(config)
        analysis.simulation_results = sim_states
        analysis.simulation_diverged = len(sim_states) < 50 and len(sim_states) > 0

        dyn_resp = self.analyze_dynamic_response(config)
        analysis.dynamic_response_results = [dyn_resp]

        analysis.is_uncontrollable = not trim.converged or analysis.simulation_diverged
        analysis.complete()
        return analysis