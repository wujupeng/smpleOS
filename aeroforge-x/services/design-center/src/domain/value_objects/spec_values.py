from __future__ import annotations

from aeroforge_common.domain.base import ValueObject


class Mass(ValueObject):
    def __init__(self, value_kg: float) -> None:
        self.value_kg = value_kg

    def __post_init__(self) -> None:
        if self.value_kg < 0:
            raise ValueError("Mass cannot be negative")


class Distance(ValueObject):
    def __init__(self, value_m: float) -> None:
        self.value_m = value_m

    @property
    def value_km(self) -> float:
        return self.value_m / 1000.0

    def __post_init__(self) -> None:
        if self.value_m < 0:
            raise ValueError("Distance cannot be negative")


class Speed(ValueObject):
    def __init__(self, value_kmh: float) -> None:
        self.value_kmh = value_kmh

    def __post_init__(self) -> None:
        if self.value_kmh < 0:
            raise ValueError("Speed cannot be negative")


class PowerType(ValueObject):
    ELECTRIC = "electric"
    HYBRID = "hybrid"
    GASOLINE = "gasoline"
    DIESEL = "diesel"

    VALID_TYPES = {ELECTRIC, HYBRID, GASOLINE, DIESEL}

    def __init__(self, value: str) -> None:
        if value not in self.VALID_TYPES:
            raise ValueError(f"Invalid power type: {value}. Must be one of {self.VALID_TYPES}")
        self.value = value


class AircraftType(ValueObject):
    FIXED_WING = "fixed_wing"
    GLIDER = "glider"
    EVTOL = "evtol"
    UAV = "uav"

    VALID_TYPES = {FIXED_WING, GLIDER, EVTOL, UAV}

    def __init__(self, value: str) -> None:
        if value not in self.VALID_TYPES:
            raise ValueError(f"Invalid aircraft type: {value}. Must be one of {self.VALID_TYPES}")
        self.value = value


class SpecStatus(ValueObject):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    FROZEN = "frozen"

    VALID_STATUSES = {DRAFT, CONFIRMED, FROZEN}

    def __init__(self, value: str = DRAFT) -> None:
        if value not in self.VALID_STATUSES:
            raise ValueError(f"Invalid spec status: {value}")
        self.value = value

    def can_transition_to(self, target: str) -> bool:
        transitions = {
            self.DRAFT: {self.CONFIRMED},
            self.CONFIRMED: {self.FROZEN},
            self.FROZEN: set(),
        }
        return target in transitions.get(self.value, set())