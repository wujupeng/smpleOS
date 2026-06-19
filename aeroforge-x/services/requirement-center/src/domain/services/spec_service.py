from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from src.domain.entities.aircraft_spec import AircraftSpec, SpecParameter
from src.domain.value_objects.enums import (
    AircraftType,
    PowerType,
    SpecStatus,
    ParameterCategory,
    ParameterPriority,
)


class SpecService:
    def create_spec(
        self,
        aircraft_type: AircraftType,
        created_by: str | None = None,
        payload_kg: Decimal | None = None,
        range_km: Decimal | None = None,
        cruise_speed_kmh: Decimal | None = None,
        takeoff_distance_m: Decimal | None = None,
        power_type: PowerType | None = None,
        budget_cny: Decimal | None = None,
    ) -> AircraftSpec:
        spec_number = f"AAF-SPEC-{uuid.uuid4().hex[:8].upper()}"
        spec = AircraftSpec(
            spec_number=spec_number,
            aircraft_type=aircraft_type,
            payload_kg=payload_kg,
            range_km=range_km,
            cruise_speed_kmh=cruise_speed_kmh,
            takeoff_distance_m=takeoff_distance_m,
            power_type=power_type,
            budget_cny=budget_cny,
            created_by=created_by,
        )
        return spec

    def validate_spec(self, spec: AircraftSpec) -> list[dict[str, Any]]:
        violations = []
        if spec.payload_kg is not None and spec.payload_kg <= 0:
            violations.append({"parameter": "payload_kg", "message": "Payload must be positive", "severity": "error"})
        if spec.payload_kg is not None and spec.payload_kg > 50000:
            violations.append({"parameter": "payload_kg", "message": "Payload exceeds 50000kg limit", "severity": "warning"})
        if spec.range_km is not None and spec.range_km <= 0:
            violations.append({"parameter": "range_km", "message": "Range must be positive", "severity": "error"})
        if spec.range_km is not None and spec.range_km > 20000:
            violations.append({"parameter": "range_km", "message": "Range exceeds 20000km limit", "severity": "warning"})
        if spec.cruise_speed_kmh is not None and spec.cruise_speed_kmh <= 0:
            violations.append({"parameter": "cruise_speed_kmh", "message": "Speed must be positive", "severity": "error"})
        if spec.power_type == PowerType.ELECTRIC and spec.cruise_speed_kmh is not None and spec.cruise_speed_kmh > 400:
            violations.append({"parameter": "cruise_speed_kmh", "message": "Electric aircraft speed typically < 400km/h", "severity": "warning"})
        if spec.takeoff_distance_m is not None and spec.takeoff_distance_m <= 0:
            violations.append({"parameter": "takeoff_distance_m", "message": "Takeoff distance must be positive", "severity": "error"})
        for param in spec.parameters:
            param_violations = param.validate()
            for v in param_violations:
                violations.append({"parameter": param.name, "message": v, "severity": "warning"})
        conflicts = self._detect_conflicts(spec)
        violations.extend(conflicts)
        return violations

    def confirm_spec(self, spec: AircraftSpec) -> AircraftSpec:
        violations = self.validate_spec(spec)
        critical = [v for v in violations if v.get("severity") == "error"]
        if critical:
            raise ValueError(f"Cannot confirm spec with critical violations: {critical}")
        spec.confirm()
        return spec

    def _detect_conflicts(self, spec: AircraftSpec) -> list[dict[str, Any]]:
        conflicts = []
        if spec.power_type == PowerType.ELECTRIC and spec.cruise_speed_kmh is not None and spec.range_km is not None:
            max_range_at_speed = 20000 / (spec.cruise_speed_kmh / 100)
            if spec.range_km > max_range_at_speed:
                conflicts.append({
                    "parameter": "range_km",
                    "message": f"Electric aircraft range {spec.range_km}km unrealistic at {spec.cruise_speed_kmh}km/h",
                    "severity": "warning",
                })
        if spec.payload_kg is not None and spec.budget_cny is not None:
            cost_per_kg = spec.budget_cny / spec.payload_kg
            if cost_per_kg < 100:
                conflicts.append({
                    "parameter": "budget_cny",
                    "message": f"Budget per kg payload ({cost_per_kg:.0f} CNY/kg) seems insufficient",
                    "severity": "warning",
                })
        return conflicts

    def derive_constraints(self, spec: AircraftSpec) -> dict[str, Any]:
        constraints = {}
        if spec.payload_kg is not None and spec.range_km is not None:
            constraints["payload_range_product"] = float(spec.payload_kg * spec.range_km)
        if spec.cruise_speed_kmh is not None and spec.range_km is not None:
            constraints["endurance_hours"] = float(spec.range_km / spec.cruise_speed_kmh)
        if spec.payload_kg is not None:
            mtow_estimate = float(spec.payload_kg * Decimal("2.5"))
            constraints["mtow_estimate_kg"] = mtow_estimate
            if spec.cruise_speed_kmh is not None:
                wing_loading = mtow_estimate * 9.81 / 50.0
                constraints["wing_loading_estimate"] = wing_loading
        if spec.power_type == PowerType.ELECTRIC and spec.payload_kg is not None and spec.range_km is not None:
            energy = float(spec.payload_kg * spec.range_km * Decimal("0.003"))
            constraints["battery_energy_estimate_kwh"] = energy
        return constraints