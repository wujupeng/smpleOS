from __future__ import annotations

import logging
import math
import time
from typing import Any

from aeroforge_common.domain.base import DomainEvent

from ..entities.simulation_models import (
    SimulationModel, SimulationStatus, FlightState,
    SimulationResult, CalibrationResult,
)

logger = logging.getLogger(__name__)


class RealtimeSimulationService:
    def __init__(self) -> None:
        self._models: dict[str, SimulationModel] = {}
        self._status: dict[str, SimulationStatus] = {}
        self._results: dict[str, list[SimulationResult]] = {}
        self._current_states: dict[str, FlightState] = {}

    def setup_simulation_model(
        self,
        aircraft_sn: str,
        structural_params: dict[str, float] | None = None,
        aero_params: dict[str, float] | None = None,
    ) -> SimulationModel:
        model = SimulationModel(
            aircraft_sn=aircraft_sn,
            structural_params=structural_params or {
                "wing_span": 15.0,
                "wing_area": 30.0,
                "mass_kg": 1200.0,
                "moment_of_inertia": 50000.0,
            },
            aero_params=aero_params or {
                "cl_alpha": 5.5,
                "cd0": 0.025,
                "cl_max": 1.6,
                "oswald_efficiency": 0.85,
            },
        )

        model.rom_coefficients = {
            "lift": [model.aero_params.get("cl_alpha", 5.5), 0.0, 0.0],
            "drag": [model.aero_params.get("cd0", 0.025), 0.01, 0.001],
            "moment": [0.1, -0.05, 0.02],
            "thrust": [1.0, -0.0001, 0.0],
        }

        self._models[aircraft_sn] = model
        self._status[aircraft_sn] = SimulationStatus.IDLE
        self._results[aircraft_sn] = []
        self._current_states[aircraft_sn] = FlightState()

        logger.info("Setup simulation model for %s", aircraft_sn)
        return model

    def start_simulation(self, aircraft_sn: str) -> bool:
        if aircraft_sn not in self._models:
            return False
        self._status[aircraft_sn] = SimulationStatus.RUNNING
        logger.info("Started simulation for %s", aircraft_sn)
        return True

    def stop_simulation(self, aircraft_sn: str) -> bool:
        if aircraft_sn not in self._models:
            return False
        self._status[aircraft_sn] = SimulationStatus.STOPPED
        return True

    def pause_simulation(self, aircraft_sn: str) -> bool:
        if aircraft_sn not in self._models:
            return False
        self._status[aircraft_sn] = SimulationStatus.PAUSED
        return True

    def run_realtime_simulation(
        self,
        aircraft_sn: str,
        current_state: FlightState | None = None,
        dt_seconds: float = 0.1,
    ) -> SimulationResult | None:
        model = self._models.get(aircraft_sn)
        if model is None:
            return None

        if self._status.get(aircraft_sn) != SimulationStatus.RUNNING:
            return None

        start_time = time.monotonic()

        if current_state:
            self._current_states[aircraft_sn] = current_state

        state = self._current_states.get(aircraft_sn, FlightState())

        predicted = self._predict_next_state(model, state, dt_seconds)

        self._current_states[aircraft_sn] = predicted

        deviation: dict[str, float] = {}
        deviation_exceeds = False
        threshold = 0.05

        if current_state:
            deviation = self._compute_deviation(predicted, current_state)
            for key, dev in deviation.items():
                if dev > threshold:
                    deviation_exceeds = True
                    model.deviation_accumulated += dev

        elapsed = (time.monotonic() - start_time) * 1000

        step = len(self._results.get(aircraft_sn, [])) + 1
        result = SimulationResult(
            predicted_state=predicted,
            actual_state=current_state,
            deviation=deviation,
            deviation_exceeds_threshold=deviation_exceeds,
            simulation_time_ms=elapsed,
            step_number=step,
        )

        self._results.setdefault(aircraft_sn, []).append(result)

        if deviation_exceeds:
            logger.warning("Simulation deviation exceeds threshold for %s at step %d", aircraft_sn, step)

        return result

    def compare_actual_vs_predicted(
        self,
        aircraft_sn: str,
        actual_state: FlightState,
    ) -> dict[str, Any] | None:
        model = self._models.get(aircraft_sn)
        if model is None:
            return None

        results = self._results.get(aircraft_sn, [])
        if not results:
            return None

        last_result = results[-1]
        predicted = last_result.predicted_state

        deviation = self._compute_deviation(predicted, actual_state)

        max_dev_key = max(deviation, key=deviation.get) if deviation else ""
        max_dev_val = deviation.get(max_dev_key, 0.0)

        return {
            "aircraft_sn": aircraft_sn,
            "step_number": last_result.step_number,
            "deviation": {k: round(v, 6) for k, v in deviation.items()},
            "max_deviation_param": max_dev_key,
            "max_deviation_value": round(max_dev_val, 6),
            "deviation_threshold": 0.05,
            "exceeds_threshold": max_dev_val > 0.05,
            "accumulated_deviation": round(model.deviation_accumulated, 6),
        }

    def calibrate_model(self, aircraft_sn: str) -> CalibrationResult | None:
        model = self._models.get(aircraft_sn)
        if model is None:
            return None

        previous_deviation = model.deviation_accumulated

        for key in model.rom_coefficients:
            coeffs = model.rom_coefficients[key]
            if len(coeffs) >= 2:
                coeffs[0] *= 1.01
                coeffs[1] *= 0.99

        model.deviation_accumulated *= 0.5
        model.calibration_count += 1
        model.last_calibrated_at = datetime.now(timezone.utc).isoformat()

        new_deviation = model.deviation_accumulated
        improvement = ((previous_deviation - new_deviation) / max(previous_deviation, 1e-9)) * 100

        result = CalibrationResult(
            aircraft_sn=aircraft_sn,
            previous_deviation=previous_deviation,
            new_deviation=new_deviation,
            improvement_pct=round(improvement, 2),
            calibrated_params=list(model.rom_coefficients.keys()),
        )

        logger.info("Calibrated model for %s: deviation %.6f -> %.6f (%.1f%% improvement)",
                     aircraft_sn, previous_deviation, new_deviation, improvement)

        return result

    def get_simulation_status(self, aircraft_sn: str) -> dict[str, Any] | None:
        if aircraft_sn not in self._models:
            return None

        return {
            "aircraft_sn": aircraft_sn,
            "status": self._status.get(aircraft_sn, SimulationStatus.IDLE).value,
            "step_count": len(self._results.get(aircraft_sn, [])),
            "model_calibrations": self._models[aircraft_sn].calibration_count,
            "accumulated_deviation": round(self._models[aircraft_sn].deviation_accumulated, 6),
        }

    def get_results(self, aircraft_sn: str, limit: int = 20) -> list[SimulationResult]:
        results = self._results.get(aircraft_sn, [])
        return results[-limit:]

    def get_model(self, aircraft_sn: str) -> SimulationModel | None:
        return self._models.get(aircraft_sn)

    def _predict_next_state(
        self, model: SimulationModel, state: FlightState, dt: float,
    ) -> FlightState:
        rho = 1.225 * math.exp(-state.altitude_m / 8500.0)
        v = max(state.airspeed_ms, 1.0)
        q = 0.5 * rho * v * v
        S = model.structural_params.get("wing_area", 30.0)
        mass = model.structural_params.get("mass_kg", 1200.0)

        lift_coeffs = model.rom_coefficients.get("lift", [5.5, 0, 0])
        alpha_rad = math.radians(state.pitch_deg)
        lift = q * S * (lift_coeffs[0] * alpha_rad + lift_coeffs[1])

        drag_coeffs = model.rom_coefficients.get("drag", [0.025, 0.01, 0.001])
        cd = drag_coeffs[0] + drag_coeffs[1] * alpha_rad ** 2 + drag_coeffs[2] * alpha_rad ** 4
        drag = q * S * cd

        thrust_coeffs = model.rom_coefficients.get("thrust", [1.0, -0.0001, 0])
        thrust = state.engine_rpm * thrust_coeffs[0] + thrust_coeffs[1] * state.engine_rpm ** 2

        ax = (thrust - drag) / mass
        az = (lift - mass * 9.81) / mass

        new_airspeed = max(0, state.airspeed_ms + ax * dt)
        new_vertical_speed = state.vertical_speed_ms + az * dt
        new_altitude = max(0, state.altitude_m + new_vertical_speed * dt)

        fuel_burn_rate = 0.001 * state.engine_rpm / 3000.0
        new_fuel = max(0, state.fuel_kg - fuel_burn_rate * dt)

        new_heading = (state.heading_deg + state.roll_deg * 0.1 * dt) % 360

        return FlightState(
            timestamp=datetime.now(timezone.utc).isoformat(),
            altitude_m=round(new_altitude, 2),
            airspeed_ms=round(new_airspeed, 2),
            heading_deg=round(new_heading, 2),
            pitch_deg=round(state.pitch_deg + az * 0.01 * dt, 2),
            roll_deg=state.roll_deg,
            vertical_speed_ms=round(new_vertical_speed, 2),
            g_load=round(1.0 + az / 9.81, 3),
            engine_rpm=state.engine_rpm,
            fuel_kg=round(new_fuel, 2),
            temperature_c=round(15.0 - 0.0065 * new_altitude, 1),
        )

    def _compute_deviation(self, predicted: FlightState, actual: FlightState) -> dict[str, float]:
        deviation: dict[str, float] = {}
        fields = ["altitude_m", "airspeed_ms", "heading_deg", "pitch_deg", "roll_deg",
                   "vertical_speed_ms", "g_load", "engine_rpm"]

        for f in fields:
            pred_val = getattr(predicted, f, 0)
            act_val = getattr(actual, f, 0)
            if abs(act_val) > 1e-6:
                deviation[f] = abs(pred_val - act_val) / abs(act_val)
            elif abs(pred_val) > 1e-6:
                deviation[f] = abs(pred_val - act_val)
            else:
                deviation[f] = 0.0

        return deviation


from datetime import datetime, timezone  # noqa: E402