"""AeroForge-X v5.0 FleetTwinAggregatorService

Aggregates 10K+ aircraft digital twins with hierarchical filtering,
health aggregation, statistical sampling, and graceful degradation.
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import numpy as np


class HealthStatus(str, Enum):
    HEALTHY = "Healthy"
    WARNING = "Warning"
    CRITICAL = "Critical"


@dataclass
class AircraftFleetEntry:
    aircraft_id: str
    tail_number: str
    aircraft_type: str
    operator: str
    region: str
    age_years: float
    mission_profile: str
    twin_instance_id: str
    registration_date: str = ""
    health_status: HealthStatus = HealthStatus.HEALTHY
    rul_engine_hours: float = 10000.0
    rul_battery_hours: float = 5000.0
    fatigue_consumption: float = 0.3

    def to_dict(self) -> dict:
        return {
            "aircraft_id": self.aircraft_id,
            "tail_number": self.tail_number,
            "aircraft_type": self.aircraft_type,
            "operator": self.operator,
            "region": self.region,
            "age_years": self.age_years,
            "mission_profile": self.mission_profile,
            "health_status": self.health_status.value,
        }


@dataclass(frozen=True)
class FleetFilter:
    aircraft_type: str | None = None
    operator: str | None = None
    region: str | None = None
    age_range: tuple[float, float] | None = None
    mission_profile: str | None = None
    health_status: HealthStatus | None = None


@dataclass(frozen=True)
class FleetHealthIndicator:
    indicator_id: str
    filter_hash: str
    total_aircraft: int
    healthy_count: int
    warning_count: int
    critical_count: int
    average_rul_hours: float
    average_fatigue_consumption: float
    confidence_interval: dict
    is_sampled: bool
    sample_size: int


@dataclass(frozen=True)
class FleetDashboard:
    total_aircraft: int
    health_summary: dict[str, int]
    region_breakdown: dict[str, int]
    operator_breakdown: dict[str, int]
    type_breakdown: dict[str, int]
    average_age: float
    average_rul_hours: float


class FleetTwinAggregatorService:

    def __init__(self) -> None:
        self._fleet: dict[str, AircraftFleetEntry] = {}
        self._last_aggregation_at: float = 0.0

    def register_aircraft(
        self,
        tail_number: str,
        aircraft_type: str,
        operator: str,
        region: str,
        age_years: float,
        mission_profile: str,
        twin_instance_id: str = "",
    ) -> AircraftFleetEntry:
        aircraft_id = f"AC-{operator[:3].upper()}-{uuid.uuid4().hex[:6].upper()}"

        entry = AircraftFleetEntry(
            aircraft_id=aircraft_id,
            tail_number=tail_number,
            aircraft_type=aircraft_type,
            operator=operator,
            region=region,
            age_years=age_years,
            mission_profile=mission_profile,
            twin_instance_id=twin_instance_id or aircraft_id,
            registration_date=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

        self._fleet[aircraft_id] = entry
        return entry

    def compute_fleet_health_indicator(
        self,
        fleet_filter: FleetFilter | None = None,
    ) -> FleetHealthIndicator:
        start = time.time()

        filtered = self._apply_filter(fleet_filter)
        filter_hash = self._compute_filter_hash(fleet_filter)

        sampled = filtered
        is_sampled = False
        sample_size = len(filtered)
        confidence_interval = {}

        if len(filtered) > 5000:
            is_sampled = True
            sample_size = min(500, len(filtered))
            indices = np.random.choice(len(filtered), sample_size, replace=False)
            sampled = [filtered[i] for i in indices]
            confidence_interval = self._compute_confidence_interval(sampled, len(filtered))

        healthy = sum(1 for a in sampled if a.health_status == HealthStatus.HEALTHY)
        warning = sum(1 for a in sampled if a.health_status == HealthStatus.WARNING)
        critical = sum(1 for a in sampled if a.health_status == HealthStatus.CRITICAL)

        avg_rul = 0.0
        avg_fatigue = 0.0
        if sampled:
            avg_rul = sum(a.rul_engine_hours for a in sampled) / len(sampled)
            avg_fatigue = sum(a.fatigue_consumption for a in sampled) / len(sampled)

        self._last_aggregation_at = time.time()

        return FleetHealthIndicator(
            indicator_id=f"FHI-{uuid.uuid4().hex[:8].upper()}",
            filter_hash=filter_hash,
            total_aircraft=len(filtered),
            healthy_count=healthy,
            warning_count=warning,
            critical_count=critical,
            average_rul_hours=avg_rul,
            average_fatigue_consumption=avg_fatigue,
            confidence_interval=confidence_interval,
            is_sampled=is_sampled,
            sample_size=sample_size,
        )

    def get_fleet_status_dashboard(self) -> FleetDashboard:
        aircraft = list(self._fleet.values())

        health_summary: dict[str, int] = {}
        region_breakdown: dict[str, int] = {}
        operator_breakdown: dict[str, int] = {}
        type_breakdown: dict[str, int] = {}

        for a in aircraft:
            health_summary[a.health_status.value] = health_summary.get(a.health_status.value, 0) + 1
            region_breakdown[a.region] = region_breakdown.get(a.region, 0) + 1
            operator_breakdown[a.operator] = operator_breakdown.get(a.operator, 0) + 1
            type_breakdown[a.aircraft_type] = type_breakdown.get(a.aircraft_type, 0) + 1

        avg_age = sum(a.age_years for a in aircraft) / len(aircraft) if aircraft else 0.0
        avg_rul = sum(a.rul_engine_hours for a in aircraft) / len(aircraft) if aircraft else 0.0

        return FleetDashboard(
            total_aircraft=len(aircraft),
            health_summary=health_summary,
            region_breakdown=region_breakdown,
            operator_breakdown=operator_breakdown,
            type_breakdown=type_breakdown,
            average_age=avg_age,
            average_rul_hours=avg_rul,
        )

    def drill_down_aircraft(self, aircraft_id: str) -> Optional[AircraftFleetEntry]:
        return self._fleet.get(aircraft_id)

    def _apply_filter(self, fleet_filter: FleetFilter | None) -> list[AircraftFleetEntry]:
        if fleet_filter is None:
            return list(self._fleet.values())

        result = []
        for a in self._fleet.values():
            if fleet_filter.aircraft_type and a.aircraft_type != fleet_filter.aircraft_type:
                continue
            if fleet_filter.operator and a.operator != fleet_filter.operator:
                continue
            if fleet_filter.region and a.region != fleet_filter.region:
                continue
            if fleet_filter.age_range:
                if not (fleet_filter.age_range[0] <= a.age_years <= fleet_filter.age_range[1]):
                    continue
            if fleet_filter.mission_profile and a.mission_profile != fleet_filter.mission_profile:
                continue
            if fleet_filter.health_status and a.health_status != fleet_filter.health_status:
                continue
            result.append(a)
        return result

    def _compute_filter_hash(self, fleet_filter: FleetFilter | None) -> str:
        if fleet_filter is None:
            return "all"
        parts = [
            fleet_filter.aircraft_type or "*",
            fleet_filter.operator or "*",
            fleet_filter.region or "*",
            str(fleet_filter.age_range or "*"),
            fleet_filter.mission_profile or "*",
            fleet_filter.health_status.value if fleet_filter.health_status else "*",
        ]
        return "-".join(parts)

    def _compute_confidence_interval(
        self,
        sample: list[AircraftFleetEntry],
        population_size: int,
    ) -> dict:
        if not sample:
            return {}

        rul_values = [a.rul_engine_hours for a in sample]
        mean = np.mean(rul_values)
        std = np.std(rul_values, ddof=1) if len(rul_values) > 1 else 0.0

        fpc = 1.0
        if population_size > len(sample):
            fpc = math.sqrt((population_size - len(sample)) / (population_size - 1))

        se = (std / math.sqrt(len(sample))) * fpc if len(sample) > 0 else 0.0
        z = 1.96

        return {
            "mean_rul_hours": float(mean),
            "lower_bound_95": float(mean - z * se),
            "upper_bound_95": float(mean + z * se),
            "standard_error": float(se),
        }