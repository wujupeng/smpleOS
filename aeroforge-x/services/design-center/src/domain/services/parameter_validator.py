from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Violation:
    parameter: str
    message: str
    severity: str = "error"
    suggestion: str = ""


class ParameterValidator(ABC):
    @abstractmethod
    def validate(self, params: dict[str, Any]) -> list[Violation]:
        ...


class CompletenessValidator(ParameterValidator):
    REQUIRED_FIELDS = ["payload_kg", "range_km", "cruise_speed_kmh", "takeoff_distance_m", "power_type"]

    def validate(self, params: dict[str, Any]) -> list[Violation]:
        violations: list[Violation] = []
        for field_name in self.REQUIRED_FIELDS:
            value = params.get(field_name)
            if value is None or value == "":
                violations.append(Violation(
                    parameter=field_name,
                    message=f"Required parameter '{field_name}' is missing",
                    severity="error",
                    suggestion=f"Please provide a value for {field_name}",
                ))
        return violations


class RangeValidator(ParameterValidator):
    RANGES = {
        "payload_kg": (1, 50000, "kg"),
        "range_km": (10, 20000, "km"),
        "cruise_speed_kmh": (50, 900, "km/h"),
        "takeoff_distance_m": (10, 3000, "m"),
    }

    def validate(self, params: dict[str, Any]) -> list[Violation]:
        violations: list[Violation] = []
        for field_name, (min_val, max_val, unit) in self.RANGES.items():
            value = params.get(field_name)
            if value is not None:
                if not isinstance(value, (int, float)):
                    violations.append(Violation(
                        parameter=field_name,
                        message=f"'{field_name}' must be a number",
                        severity="error",
                    ))
                elif value < min_val or value > max_val:
                    violations.append(Violation(
                        parameter=field_name,
                        message=f"'{field_name}' value {value} {unit} is out of range [{min_val}, {max_val}] {unit}",
                        severity="error",
                        suggestion=f"Adjust {field_name} to be between {min_val} and {max_val} {unit}",
                    ))
        return violations


class ConsistencyValidator(ParameterValidator):
    def validate(self, params: dict[str, Any]) -> list[Violation]:
        violations: list[Violation] = []
        power_type = params.get("power_type", "")
        cruise_speed = params.get("cruise_speed_kmh")

        if power_type == "electric" and cruise_speed is not None and cruise_speed > 400:
            violations.append(Violation(
                parameter="cruise_speed_kmh",
                message=f"Electric aircraft with cruise speed {cruise_speed} km/h is not practical",
                severity="error",
                suggestion="Electric aircraft typically have cruise speeds below 400 km/h. Consider hybrid propulsion for higher speeds.",
            ))

        payload = params.get("payload_kg")
        range_km = params.get("range_km")
        budget = params.get("budget_cny")

        if payload and range_km and budget:
            payload_range_product = payload * range_km
            if payload_range_product > 0 and budget > 0:
                cost_per_ton_km = budget / (payload_range_product / 1000)
                if cost_per_ton_km < 0.5:
                    violations.append(Violation(
                        parameter="budget_cny",
                        message=f"Budget {budget} CNY is insufficient for {payload}kg payload and {range_km}km range",
                        severity="warning",
                        suggestion="Increase budget or reduce payload/range requirements",
                    ))

        return violations


class ValidationEngine:
    def __init__(self) -> None:
        self._validators: list[ParameterValidator] = [
            CompletenessValidator(),
            RangeValidator(),
            ConsistencyValidator(),
        ]

    def validate(self, params: dict[str, Any]) -> list[Violation]:
        all_violations: list[Violation] = []
        for validator in self._validators:
            all_violations.extend(validator.validate(params))
        return all_violations