from __future__ import annotations

from typing import Any

from ..entities.aircraft_spec import AircraftSpec
from .parameter_validator import ValidationEngine


class SpecDomainService:
    def __init__(self) -> None:
        self._validation_engine = ValidationEngine()

    def validate_parameters(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        violations = self._validation_engine.validate(params)
        return [
            {
                "parameter": v.parameter,
                "message": v.message,
                "severity": v.severity,
                "suggestion": v.suggestion,
            }
            for v in violations
        ]

    def derive_constraints(self, spec: AircraftSpec) -> dict[str, Any]:
        constraints: dict[str, Any] = {}
        if spec.payload_kg > 0 and spec.range_km > 0:
            constraints["payload_range_product"] = spec.payload_kg * spec.range_km
        if spec.cruise_speed_kmh > 0 and spec.range_km > 0:
            constraints["endurance_hours"] = spec.range_km / spec.cruise_speed_kmh
        if spec.payload_kg > 0 and spec.cruise_speed_kmh > 0:
            constraints["wing_loading_estimate"] = min(spec.payload_kg * 9.81 / 20.0, 500)
        if spec.power_type == "electric":
            constraints["battery_energy_estimate_kwh"] = spec.payload_kg * spec.range_km * 0.005
        return constraints

    def generate_spec_document(self, spec: AircraftSpec) -> dict[str, Any]:
        constraints = self.derive_constraints(spec)
        spec.derived_constraints = constraints
        return {
            "spec_id": spec.id,
            "spec_code": spec.spec_code,
            "aircraft_type": spec.aircraft_type,
            "requirements": {
                "payload_kg": spec.payload_kg,
                "range_km": spec.range_km,
                "cruise_speed_kmh": spec.cruise_speed_kmh,
                "takeoff_distance_m": spec.takeoff_distance_m,
                "power_type": spec.power_type,
                "budget_cny": spec.budget_cny,
                "material_id": spec.material_id,
                "certification_level_id": spec.certification_level_id,
            },
            "derived_constraints": constraints,
            "status": spec.status,
        }