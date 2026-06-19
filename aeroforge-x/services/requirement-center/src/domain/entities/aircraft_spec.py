from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from src.domain.value_objects.enums import (
    AircraftType,
    PowerType,
    SpecStatus,
    ParameterCategory,
    ParameterPriority,
)


@dataclass
class SpecParameter:
    parameter_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    category: ParameterCategory = ParameterCategory.PERFORMANCE
    value: Decimal | None = None
    unit: str = ""
    tolerance: Decimal | None = None
    priority: ParameterPriority = ParameterPriority.MEDIUM
    is_required: bool = False
    validation_rules: list[dict[str, Any]] = field(default_factory=list)
    dependencies: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def update_value(self, new_value: Decimal, new_tolerance: Decimal | None = None) -> None:
        self.value = new_value
        if new_tolerance is not None:
            self.tolerance = new_tolerance
        self.updated_at = datetime.utcnow()

    def validate(self) -> list[str]:
        violations = []
        for rule in self.validation_rules:
            rule_type = rule.get("type")
            if rule_type == "range":
                min_val = rule.get("min")
                max_val = rule.get("max")
                if self.value is not None and min_val is not None and max_val is not None:
                    if not (Decimal(str(min_val)) <= self.value <= Decimal(str(max_val))):
                        violations.append(
                            f"Parameter '{self.name}' value {self.value} outside range [{min_val}, {max_val}]"
                        )
            elif rule_type == "required" and self.value is None:
                violations.append(f"Parameter '{self.name}' is required but has no value")
        return violations


@dataclass
class AircraftSpec:
    spec_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    spec_number: str = ""
    aircraft_type: AircraftType = AircraftType.FIXED_WING
    version: int = 1
    status: SpecStatus = SpecStatus.DRAFT
    payload_kg: Decimal | None = None
    range_km: Decimal | None = None
    cruise_speed_kmh: Decimal | None = None
    takeoff_distance_m: Decimal | None = None
    power_type: PowerType | None = None
    budget_cny: Decimal | None = None
    material_id: str | None = None
    certification_level_id: str | None = None
    derived_constraints: dict[str, Any] = field(default_factory=dict)
    parameters: list[SpecParameter] = field(default_factory=list)
    created_by: str | None = None
    approved_by: str | None = None
    confirmed_at: datetime | None = None
    frozen_at: datetime | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    domain_events: list[dict[str, Any]] = field(default_factory=list)

    def add_parameter(self, param: SpecParameter) -> None:
        if self.status not in (SpecStatus.DRAFT, SpecStatus.REJECTED):
            raise ValueError(f"Cannot add parameters to spec in {self.status.value} status")
        self.parameters.append(param)
        self.updated_at = datetime.utcnow()

    def update_parameter(self, parameter_id: str, value: Decimal, tolerance: Decimal | None = None) -> None:
        if self.status not in (SpecStatus.DRAFT, SpecStatus.REJECTED):
            raise ValueError(f"Cannot update parameters of spec in {self.status.value} status")
        for param in self.parameters:
            if param.parameter_id == parameter_id:
                param.update_value(value, tolerance)
                self.updated_at = datetime.utcnow()
                return
        raise KeyError(f"Parameter {parameter_id} not found")

    def remove_parameter(self, parameter_id: str) -> None:
        if self.status not in (SpecStatus.DRAFT, SpecStatus.REJECTED):
            raise ValueError(f"Cannot remove parameters from spec in {self.status.value} status")
        self.parameters = [p for p in self.parameters if p.parameter_id != parameter_id]
        self.updated_at = datetime.utcnow()

    def submit_for_review(self) -> None:
        if not self.status.can_transition_to(SpecStatus.SUBMITTED):
            raise ValueError(f"Cannot submit spec from {self.status.value} status")
        missing = [p.name for p in self.parameters if p.is_required and p.value is None]
        if missing:
            raise ValueError(f"Required parameters missing values: {', '.join(missing)}")
        self.status = SpecStatus.SUBMITTED
        self.updated_at = datetime.utcnow()

    def approve(self, approver: str) -> None:
        if not self.status.can_transition_to(SpecStatus.APPROVED):
            raise ValueError(f"Cannot approve spec from {self.status.value} status")
        self.status = SpecStatus.APPROVED
        self.approved_by = approver
        self.updated_at = datetime.utcnow()

    def reject(self) -> None:
        if not self.status.can_transition_to(SpecStatus.REJECTED):
            raise ValueError(f"Cannot reject spec from {self.status.value} status")
        self.status = SpecStatus.REJECTED
        self.updated_at = datetime.utcnow()

    def confirm(self) -> None:
        if not self.status.can_transition_to(SpecStatus.CONFIRMED):
            raise ValueError(f"Cannot confirm spec from {self.status.value} status")
        self.status = SpecStatus.CONFIRMED
        self.confirmed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.domain_events.append({
            "event_type": "aircraft.spec.confirmed",
            "spec_id": self.spec_id,
            "spec_number": self.spec_number,
            "aircraft_type": self.aircraft_type.value,
            "version": self.version,
        })

    def freeze(self) -> None:
        if not self.status.can_transition_to(SpecStatus.FROZEN):
            raise ValueError(f"Cannot freeze spec from {self.status.value} status")
        self.status = SpecStatus.FROZEN
        self.frozen_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def update_parameters(
        self,
        payload_kg: Decimal | None = None,
        range_km: Decimal | None = None,
        cruise_speed_kmh: Decimal | None = None,
        takeoff_distance_m: Decimal | None = None,
        power_type: PowerType | None = None,
        budget_cny: Decimal | None = None,
    ) -> None:
        if self.status not in (SpecStatus.DRAFT, SpecStatus.REJECTED):
            raise ValueError(f"Cannot update spec in {self.status.value} status")
        if payload_kg is not None:
            self.payload_kg = payload_kg
        if range_km is not None:
            self.range_km = range_km
        if cruise_speed_kmh is not None:
            self.cruise_speed_kmh = cruise_speed_kmh
        if takeoff_distance_m is not None:
            self.takeoff_distance_m = takeoff_distance_m
        if power_type is not None:
            self.power_type = power_type
        if budget_cny is not None:
            self.budget_cny = budget_cny
        self.updated_at = datetime.utcnow()

    def clear_events(self) -> list[dict[str, Any]]:
        events = self.domain_events.copy()
        self.domain_events.clear()
        return events