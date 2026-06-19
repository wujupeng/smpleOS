from __future__ import annotations

from typing import Any


UNIT_FACTORS: dict[str, dict[str, dict[str, Any]]] = {
    "length": {
        "m": {"factor": 1.0, "offset": 0.0},
        "mm": {"factor": 0.001, "offset": 0.0},
        "ft": {"factor": 0.3048, "offset": 0.0},
        "in": {"factor": 0.0254, "offset": 0.0},
        "cm": {"factor": 0.01, "offset": 0.0},
    },
    "mass": {
        "kg": {"factor": 1.0, "offset": 0.0},
        "lb": {"factor": 0.453592, "offset": 0.0},
        "g": {"factor": 0.001, "offset": 0.0},
    },
    "force": {
        "N": {"factor": 1.0, "offset": 0.0},
        "kN": {"factor": 1000.0, "offset": 0.0},
        "lbf": {"factor": 4.44822, "offset": 0.0},
    },
    "pressure": {
        "Pa": {"factor": 1.0, "offset": 0.0},
        "MPa": {"factor": 1_000_000.0, "offset": 0.0},
        "psi": {"factor": 6894.76, "offset": 0.0},
        "kPa": {"factor": 1000.0, "offset": 0.0},
    },
    "temperature": {
        "K": {"factor": 1.0, "offset": 0.0},
        "C": {"factor": 1.0, "offset": 273.15},
        "F": {"factor": 5 / 9, "offset": 255.372},
    },
    "angle": {
        "rad": {"factor": 1.0, "offset": 0.0},
        "deg": {"factor": 0.0174533, "offset": 0.0},
    },
    "time": {
        "s": {"factor": 1.0, "offset": 0.0},
        "min": {"factor": 60.0, "offset": 0.0},
        "h": {"factor": 3600.0, "offset": 0.0},
    },
    "speed": {
        "m/s": {"factor": 1.0, "offset": 0.0},
        "km/h": {"factor": 0.277778, "offset": 0.0},
        "kt": {"factor": 0.514444, "offset": 0.0},
        "ft/s": {"factor": 0.3048, "offset": 0.0},
    },
    "power": {
        "W": {"factor": 1.0, "offset": 0.0},
        "kW": {"factor": 1000.0, "offset": 0.0},
        "hp": {"factor": 745.7, "offset": 0.0},
    },
    "energy": {
        "J": {"factor": 1.0, "offset": 0.0},
        "kJ": {"factor": 1000.0, "offset": 0.0},
        "kWh": {"factor": 3_600_000.0, "offset": 0.0},
    },
}

SI_BASE_UNITS: dict[str, str] = {
    "length": "m",
    "mass": "kg",
    "force": "N",
    "pressure": "Pa",
    "temperature": "K",
    "angle": "rad",
    "time": "s",
    "speed": "m/s",
    "power": "W",
    "energy": "J",
}


class UnitConversionService:

    @staticmethod
    def convert_unit(value: float, from_unit: str, to_unit: str) -> float:
        if from_unit == to_unit:
            return value

        dimension = UnitConversionService._find_dimension(from_unit, to_unit)
        if dimension is None:
            raise ValueError(f"Incompatible units: {from_unit} and {to_unit} belong to different dimensions")

        si_value = UnitConversionService._to_si(value, from_unit, dimension)
        return UnitConversionService._from_si(si_value, to_unit, dimension)

    @staticmethod
    def validate_dimensional_compatibility(unit1: str, unit2: str) -> bool:
        return UnitConversionService._find_dimension(unit1, unit2) is not None

    @staticmethod
    def get_canonical_value(value: float, unit: str) -> tuple[float, str]:
        dimension = UnitConversionService._find_dimension_by_unit(unit)
        if dimension is None:
            raise ValueError(f"Unknown unit: {unit}")
        si_unit = SI_BASE_UNITS[dimension]
        si_value = UnitConversionService._to_si(value, unit, dimension)
        return si_value, si_unit

    @staticmethod
    def get_display_value(si_value: float, target_unit: str) -> float:
        dimension = UnitConversionService._find_dimension_by_unit(target_unit)
        if dimension is None:
            raise ValueError(f"Unknown unit: {target_unit}")
        return UnitConversionService._from_si(si_value, target_unit, dimension)

    @staticmethod
    def get_supported_units() -> dict[str, list[str]]:
        return {dim: list(units.keys()) for dim, units in UNIT_FACTORS.items()}

    @staticmethod
    def _find_dimension(unit1: str, unit2: str) -> str | None:
        for dim, units in UNIT_FACTORS.items():
            if unit1 in units and unit2 in units:
                return dim
        return None

    @staticmethod
    def _find_dimension_by_unit(unit: str) -> str | None:
        for dim, units in UNIT_FACTORS.items():
            if unit in units:
                return dim
        return None

    @staticmethod
    def _to_si(value: float, from_unit: str, dimension: str) -> float:
        factor_info = UNIT_FACTORS[dimension].get(from_unit)
        if factor_info is None:
            raise ValueError(f"Unknown unit '{from_unit}' for dimension '{dimension}'")
        return value * factor_info["factor"] + factor_info["offset"]

    @staticmethod
    def _from_si(si_value: float, to_unit: str, dimension: str) -> float:
        factor_info = UNIT_FACTORS[dimension].get(to_unit)
        if factor_info is None:
            raise ValueError(f"Unknown unit '{to_unit}' for dimension '{dimension}'")
        return (si_value - factor_info["offset"]) / factor_info["factor"]