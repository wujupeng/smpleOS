from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from src.domain.entities.aircraft_spec import AircraftSpec, SpecParameter


@dataclass
class SensitivityResult:
    parameter_name: str
    baseline_value: Decimal | None
    perturbation: Decimal
    sensitivity_index: float
    influence_rank: int = 0
    performance_impact: dict[str, float] = field(default_factory=dict)


class SensitivityAnalysisService:
    def run_sensitivity_analysis(
        self,
        spec: AircraftSpec,
        parameters: list[str] | None = None,
        perturbation_pct: float = 0.05,
    ) -> list[SensitivityResult]:
        if parameters is None:
            parameters = [p.name for p in spec.parameters if p.value is not None]
        baseline_performance = self._evaluate_performance(spec)
        results: list[SensitivityResult] = []
        for param_name in parameters:
            param = self._find_parameter(spec, param_name)
            if param is None or param.value is None:
                continue
            baseline_val = param.value
            perturbation = baseline_val * Decimal(str(perturbation_pct))
            pos_spec = self._clone_with_override(spec, param_name, baseline_val + perturbation)
            neg_spec = self._clone_with_override(spec, param_name, baseline_val - perturbation)
            pos_perf = self._evaluate_performance(pos_spec)
            neg_perf = self._evaluate_performance(neg_spec)
            impact: dict[str, float] = {}
            for key in baseline_performance:
                if key in pos_perf and key in neg_perf:
                    central_diff = (pos_perf[key] - neg_perf[key]) / (2 * float(perturbation))
                    impact[key] = round(central_diff, 6)
            sensitivity_idx = sum(abs(v) for v in impact.values()) / len(impact) if impact else 0.0
            results.append(SensitivityResult(
                parameter_name=param_name,
                baseline_value=baseline_val,
                perturbation=perturbation,
                sensitivity_index=round(sensitivity_idx, 6),
                performance_impact=impact,
            ))
        results.sort(key=lambda r: r.sensitivity_index, reverse=True)
        for i, r in enumerate(results):
            r.influence_rank = i + 1
        return results

    def _evaluate_performance(self, spec: AircraftSpec) -> dict[str, float]:
        perf: dict[str, float] = {}
        if spec.payload_kg is not None and spec.range_km is not None:
            perf["payload_range_product"] = float(spec.payload_kg * spec.range_km)
        if spec.cruise_speed_kmh is not None and spec.range_km is not None:
            perf["endurance_hours"] = float(spec.range_km / spec.cruise_speed_kmh)
        if spec.payload_kg is not None:
            mtow = float(spec.payload_kg) * 2.5
            perf["mtow_estimate"] = mtow
            if spec.cruise_speed_kmh is not None:
                perf["wing_loading_estimate"] = mtow * 9.81 / 50.0
        if spec.takeoff_distance_m is not None and spec.cruise_speed_kmh is not None:
            perf["takeoff_performance_index"] = float(spec.cruise_speed_kmh) / float(spec.takeoff_distance_m)
        return perf

    def _find_parameter(self, spec: AircraftSpec, name: str) -> SpecParameter | None:
        for p in spec.parameters:
            if p.name == name:
                return p
        return None

    def _clone_with_override(self, spec: AircraftSpec, param_name: str, new_value: Decimal) -> AircraftSpec:
        import copy
        cloned = copy.deepcopy(spec)
        for p in cloned.parameters:
            if p.name == param_name:
                p.value = new_value
                break
        if param_name == "payload_kg":
            cloned.payload_kg = new_value
        elif param_name == "range_km":
            cloned.range_km = new_value
        elif param_name == "cruise_speed_kmh":
            cloned.cruise_speed_kmh = new_value
        elif param_name == "takeoff_distance_m":
            cloned.takeoff_distance_m = new_value
        return cloned