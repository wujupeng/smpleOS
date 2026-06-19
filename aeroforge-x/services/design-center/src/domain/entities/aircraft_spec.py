from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from aeroforge_common.domain.base import AggregateRoot, DomainEvent
from aeroforge_common.utils.helpers import generate_code

from ..value_objects import AircraftType, Distance, Mass, PowerType, SpecStatus, Speed


class AircraftSpec(AggregateRoot):
    def __init__(
        self,
        spec_id: str | None = None,
        aircraft_type: str = AircraftType.FIXED_WING,
        payload_kg: float = 0.0,
        range_km: float = 0.0,
        cruise_speed_kmh: float = 0.0,
        takeoff_distance_m: float = 0.0,
        power_type: str = PowerType.ELECTRIC,
        budget_cny: float | None = None,
        material_id: str | None = None,
        certification_level_id: str | None = None,
        created_by: str = "",
    ) -> None:
        super().__init__(spec_id)
        self.spec_code: str = generate_code("AAF-SPEC")
        self.aircraft_type: str = aircraft_type
        self.payload_kg: float = payload_kg
        self.range_km: float = range_km
        self.cruise_speed_kmh: float = cruise_speed_kmh
        self.takeoff_distance_m: float = takeoff_distance_m
        self.power_type: str = power_type
        self.budget_cny: float | None = budget_cny
        self.material_id: str | None = material_id
        self.certification_level_id: str | None = certification_level_id
        self.status: str = SpecStatus.DRAFT
        self.derived_constraints: dict[str, Any] = {}
        self.created_by: str = created_by
        self.confirmed_at: datetime | None = None
        self.frozen_at: datetime | None = None
        self.created_at: datetime = datetime.now(timezone.utc)
        self.updated_at: datetime = datetime.now(timezone.utc)

    def confirm(self) -> None:
        status = SpecStatus(self.status)
        if not status.can_transition_to(SpecStatus.CONFIRMED):
            raise ValueError(f"Cannot confirm spec in status '{self.status}'. Must be in 'draft' status.")
        self.status = SpecStatus.CONFIRMED
        self.confirmed_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        event = DomainEvent(
            event_type="aircraft.spec.confirmed",
            aggregate_id=self.id,
            payload={
                "spec_id": self.id,
                "spec_code": self.spec_code,
                "aircraft_type": self.aircraft_type,
                "payload_kg": self.payload_kg,
                "range_km": self.range_km,
                "cruise_speed_kmh": self.cruise_speed_kmh,
                "power_type": self.power_type,
                "confirmed_at": self.confirmed_at.isoformat(),
            },
        )
        self.add_domain_event(event)

    def freeze(self) -> None:
        status = SpecStatus(self.status)
        if not status.can_transition_to(SpecStatus.FROZEN):
            raise ValueError(f"Cannot freeze spec in status '{self.status}'. Must be in 'confirmed' status.")
        self.status = SpecStatus.FROZEN
        self.frozen_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def update_parameters(
        self,
        payload_kg: float | None = None,
        range_km: float | None = None,
        cruise_speed_kmh: float | None = None,
        takeoff_distance_m: float | None = None,
        power_type: str | None = None,
        budget_cny: float | None = None,
        material_id: str | None = None,
        certification_level_id: str | None = None,
        aircraft_type: str | None = None,
    ) -> None:
        if self.status != SpecStatus.DRAFT:
            raise ValueError(f"Cannot update spec in status '{self.status}'. Must be in 'draft' status.")
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
        if material_id is not None:
            self.material_id = material_id
        if certification_level_id is not None:
            self.certification_level_id = certification_level_id
        if aircraft_type is not None:
            self.aircraft_type = aircraft_type
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "spec_code": self.spec_code,
            "aircraft_type": self.aircraft_type,
            "payload_kg": self.payload_kg,
            "range_km": self.range_km,
            "cruise_speed_kmh": self.cruise_speed_kmh,
            "takeoff_distance_m": self.takeoff_distance_m,
            "power_type": self.power_type,
            "budget_cny": self.budget_cny,
            "material_id": self.material_id,
            "certification_level_id": self.certification_level_id,
            "status": self.status,
            "derived_constraints": self.derived_constraints,
            "created_by": self.created_by,
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
            "frozen_at": self.frozen_at.isoformat() if self.frozen_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }