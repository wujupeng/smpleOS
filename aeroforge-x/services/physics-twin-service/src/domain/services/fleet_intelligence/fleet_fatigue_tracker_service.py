"""AeroForge-X v5.0 FleetFatigueTrackerService

Tracks fleet fatigue life using Miner's cumulative damage rule,
rainflow counting, per-flight updates, and fatigue-operations correlation.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from typing import Optional

import numpy as np


@dataclass(frozen=True)
class FlightLoadData:
    flight_id: str
    aircraft_id: str
    flight_hours: float
    load_factor_spectrum: list[float]
    max_load_factor: float
    min_load_factor: float
    gust_load_cycles: int = 0
    maneuver_load_cycles: int = 0


@dataclass(frozen=True)
class FatigueLifePrediction:
    aircraft_id: str
    cumulative_damage: float
    remaining_fatigue_life_hours: float
    consumption_rate_per_flight_hour: float
    is_warning: bool
    critical_locations: list[str]


@dataclass(frozen=True)
class FleetFatigueDistribution:
    total_aircraft: int
    p10_remaining_hours: float
    p50_remaining_hours: float
    p90_remaining_hours: float
    avg_cumulative_damage: float
    warning_count: int


@dataclass(frozen=True)
class FatigueOperationsCorrelation:
    mission_type: str
    avg_consumption_rate: float
    avg_max_load_factor: float
    sample_count: int
    correlation_coefficient: float


class MinerRuleEngine:

    def __init__(self, miner_limit: float = 1.0) -> None:
        self.miner_limit = miner_limit
        self._sn_curves: dict[str, dict] = {
            "wing_root": {"A": 1000.0, "m": 3.0, "N_endurance": 1e7},
            "fuselage_frame": {"A": 800.0, "m": 3.5, "N_endurance": 1e7},
            "wing_skin": {"A": 600.0, "m": 4.0, "N_endurance": 1e7},
        }

    def compute_cumulative_damage(
        self,
        load_spectrum: list[float],
        location: str = "wing_root",
    ) -> float:
        sn = self._sn_curves.get(location, self._sn_curves["wing_root"])
        A = sn["A"]
        m = sn["m"]
        N_end = sn["N_endurance"]

        damage = 0.0
        for load_factor in load_spectrum:
            stress = abs(load_factor) * 100.0
            if stress < A / (N_end ** (1.0 / m)):
                continue
            if stress > 0:
                N_cycles = (A / stress) ** m
                if N_cycles > 0:
                    damage += 1.0 / N_cycles

        return damage

    def compute_remaining_life(
        self,
        cumulative_damage: float,
        consumption_rate: float,
    ) -> float:
        if consumption_rate <= 0:
            return float("inf")
        remaining_damage = self.miner_limit - cumulative_damage
        if remaining_damage <= 0:
            return 0.0
        return remaining_damage / consumption_rate


class FleetFatigueTrackerService:

    def __init__(self) -> None:
        self._miner_engine = MinerRuleEngine()
        self._aircraft_damage: dict[str, dict] = {}
        self._flight_history: dict[str, list[FlightLoadData]] = {}

    def update_fatigue_damage(
        self,
        flight_data: FlightLoadData,
    ) -> FatigueLifePrediction:
        aircraft_id = flight_data.aircraft_id

        if aircraft_id not in self._aircraft_damage:
            self._aircraft_damage[aircraft_id] = {
                "cumulative_damage": 0.0,
                "total_flight_hours": 0.0,
                "flight_count": 0,
            }

        state = self._aircraft_damage[aircraft_id]

        spectrum = flight_data.load_factor_spectrum
        if not spectrum:
            spectrum = [flight_data.max_load_factor, flight_data.min_load_factor]

        rainflow_cycles = self._rainflow_count(spectrum)
        flight_damage = self._miner_engine.compute_cumulative_damage(rainflow_cycles)

        state["cumulative_damage"] += flight_damage
        state["total_flight_hours"] += flight_data.flight_hours
        state["flight_count"] += 1

        self._flight_history.setdefault(aircraft_id, []).append(flight_data)

        consumption_rate = 0.0
        if state["total_flight_hours"] > 0:
            consumption_rate = state["cumulative_damage"] / state["total_flight_hours"]

        remaining_life = self._miner_engine.compute_remaining_life(
            state["cumulative_damage"], consumption_rate,
        )

        is_warning = state["cumulative_damage"] > 0.8 * self._miner_engine.miner_limit

        critical_locations = []
        if state["cumulative_damage"] > 0.5:
            critical_locations.append("wing_root")
        if state["cumulative_damage"] > 0.7:
            critical_locations.append("fuselage_frame")

        return FatigueLifePrediction(
            aircraft_id=aircraft_id,
            cumulative_damage=state["cumulative_damage"],
            remaining_fatigue_life_hours=remaining_life,
            consumption_rate_per_flight_hour=consumption_rate,
            is_warning=is_warning,
            critical_locations=critical_locations,
        )

    def get_fleet_fatigue_distribution(self) -> FleetFatigueDistribution:
        if not self._aircraft_damage:
            return FleetFatigueDistribution(
                total_aircraft=0,
                p10_remaining_hours=0.0,
                p50_remaining_hours=0.0,
                p90_remaining_hours=0.0,
                avg_cumulative_damage=0.0,
                warning_count=0,
            )

        remaining_hours: list[float] = []
        damages: list[float] = []
        warning_count = 0

        for aircraft_id, state in self._aircraft_damage.items():
            consumption = state["cumulative_damage"] / state["total_flight_hours"] if state["total_flight_hours"] > 0 else 0
            remaining = self._miner_engine.compute_remaining_life(state["cumulative_damage"], consumption)
            remaining_hours.append(remaining)
            damages.append(state["cumulative_damage"])
            if state["cumulative_damage"] > 0.8:
                warning_count += 1

        arr = np.array(remaining_hours)

        return FleetFatigueDistribution(
            total_aircraft=len(self._aircraft_damage),
            p10_remaining_hours=float(np.percentile(arr, 10)) if len(arr) > 0 else 0.0,
            p50_remaining_hours=float(np.percentile(arr, 50)) if len(arr) > 0 else 0.0,
            p90_remaining_hours=float(np.percentile(arr, 90)) if len(arr) > 0 else 0.0,
            avg_cumulative_damage=float(np.mean(damages)) if damages else 0.0,
            warning_count=warning_count,
        )

    def correlate_fatigue_with_operations(
        self,
        aircraft_mission_map: dict[str, str],
    ) -> list[FatigueOperationsCorrelation]:
        mission_data: dict[str, list[dict]] = {}

        for aircraft_id, mission in aircraft_mission_map.items():
            state = self._aircraft_damage.get(aircraft_id)
            if state is None:
                continue

            consumption = state["cumulative_damage"] / state["total_flight_hours"] if state["total_flight_hours"] > 0 else 0
            flights = self._flight_history.get(aircraft_id, [])
            max_lf = max((f.max_load_factor for f in flights), default=1.0)

            mission_data.setdefault(mission, []).append({
                "consumption_rate": consumption,
                "max_load_factor": max_lf,
            })

        correlations: list[FatigueOperationsCorrelation] = []
        for mission, data_points in mission_data.items():
            if not data_points:
                continue

            avg_consumption = sum(d["consumption_rate"] for d in data_points) / len(data_points)
            avg_max_lf = sum(d["max_load_factor"] for d in data_points) / len(data_points)

            if len(data_points) >= 2:
                x = np.array([d["max_load_factor"] for d in data_points])
                y = np.array([d["consumption_rate"] for d in data_points])
                if np.std(x) > 0 and np.std(y) > 0:
                    corr = float(np.corrcoef(x, y)[0, 1])
                else:
                    corr = 0.0
            else:
                corr = 0.0

            correlations.append(FatigueOperationsCorrelation(
                mission_type=mission,
                avg_consumption_rate=avg_consumption,
                avg_max_load_factor=avg_max_lf,
                sample_count=len(data_points),
                correlation_coefficient=corr if not math.isnan(corr) else 0.0,
            ))

        return correlations

    def emit_fatigue_warning(self, aircraft_id: str) -> Optional[dict]:
        state = self._aircraft_damage.get(aircraft_id)
        if state is None:
            return None

        if state["cumulative_damage"] > 0.8:
            return {
                "aircraft_id": aircraft_id,
                "warning_type": "FatigueLifeWarning",
                "cumulative_damage": state["cumulative_damage"],
                "miner_limit": self._miner_engine.miner_limit,
                "damage_ratio": state["cumulative_damage"] / self._miner_engine.miner_limit,
                "message": f"Aircraft {aircraft_id} cumulative damage {state['cumulative_damage']:.3f} exceeds 80% Miner limit",
            }

        return None

    def _rainflow_count(self, spectrum: list[float]) -> list[float]:
        if not spectrum:
            return []

        peaks: list[float] = []
        for i in range(1, len(spectrum) - 1):
            if (spectrum[i] >= spectrum[i - 1] and spectrum[i] >= spectrum[i + 1]) or \
               (spectrum[i] <= spectrum[i - 1] and spectrum[i] <= spectrum[i + 1]):
                peaks.append(spectrum[i])

        if len(peaks) < 2:
            peaks = [max(spectrum), min(spectrum)]

        cycles: list[float] = []
        i = 0
        while i < len(peaks) - 1:
            range_val = abs(peaks[i + 1] - peaks[i])
            cycles.append(range_val)
            i += 2

        return cycles if cycles else [abs(max(spectrum) - min(spectrum))]