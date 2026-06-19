"""AeroForge-X v5.0 FleetOptimizerService

Optimizes fleet scheduling based on aircraft health and maintenance needs,
computes maintenance windows, and supports What-If analysis.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class MaintenanceWindow:
    window_id: str
    aircraft_id: str
    start_time: str
    end_time: str
    maintenance_type: str
    resource_availability: dict
    operational_impact: str = ""


@dataclass(frozen=True)
class FleetSchedule:
    schedule_id: str
    aircraft_assignments: dict
    maintenance_windows: list[MaintenanceWindow]
    total_operational_aircraft: int
    constraint_violations: list[dict]
    optimization_score: float


class FleetOptimizerService:

    def __init__(self) -> None:
        self._schedules: dict[str, FleetSchedule] = {}

    def optimize_fleet_schedule(
        self,
        aircraft_health: dict[str, dict],
        mission_requirements: list[dict] | None = None,
    ) -> FleetSchedule:
        assignments: dict[str, str] = {}
        windows: list[MaintenanceWindow] = []
        violations: list[dict] = []
        operational = 0

        for aircraft_id, health in aircraft_health.items():
            rul = health.get("rul_hours", 10000.0)
            status = health.get("status", "Healthy")

            if status == "Critical" or rul < 200:
                windows.append(MaintenanceWindow(
                    window_id=f"MW-{uuid.uuid4().hex[:6].upper()}",
                    aircraft_id=aircraft_id,
                    start_time="immediate",
                    end_time="+48h",
                    maintenance_type="Corrective",
                    resource_availability={"technicians": 2, "parts": "on-hand"},
                    operational_impact="Aircraft grounded",
                ))
            elif status == "Warning" or rul < 1000:
                windows.append(MaintenanceWindow(
                    window_id=f"MW-{uuid.uuid4().hex[:6].upper()}",
                    aircraft_id=aircraft_id,
                    start_time="next_window",
                    end_time="+24h",
                    maintenance_type="Preventive",
                    resource_availability={"technicians": 1, "parts": "on-order"},
                    operational_impact="Reduced availability",
                ))
                assignments[aircraft_id] = "limited_mission"
                operational += 1
            else:
                assignments[aircraft_id] = "full_mission"
                operational += 1

        if mission_requirements:
            available = [aid for aid, assign in assignments.items() if assign == "full_mission"]
            for req in mission_requirements:
                if not available:
                    violations.append({
                        "type": "InsufficientAircraft",
                        "requirement": req.get("mission_id", ""),
                        "message": "No available aircraft for mission",
                    })
                else:
                    assigned_id = available.pop(0)
                    assignments[assigned_id] = req.get("mission_id", "mission")

        score = self._compute_schedule_score(aircraft_health, assignments, violations)

        schedule = FleetSchedule(
            schedule_id=f"FS-{uuid.uuid4().hex[:8].upper()}",
            aircraft_assignments=assignments,
            maintenance_windows=windows,
            total_operational_aircraft=operational,
            constraint_violations=violations,
            optimization_score=score,
        )
        self._schedules[schedule.schedule_id] = schedule
        return schedule

    def compute_maintenance_windows(
        self,
        aircraft_id: str,
        health_data: dict,
        operational_constraints: dict | None = None,
    ) -> list[MaintenanceWindow]:
        rul = health_data.get("rul_hours", 10000.0)
        windows: list[MaintenanceWindow] = []

        if rul < 200:
            windows.append(MaintenanceWindow(
                window_id=f"MW-{uuid.uuid4().hex[:6].upper()}",
                aircraft_id=aircraft_id,
                start_time="immediate",
                end_time="+48h",
                maintenance_type="Corrective",
                resource_availability={"technicians": 2},
                operational_impact="Grounded",
            ))
        elif rul < 1000:
            windows.append(MaintenanceWindow(
                window_id=f"MW-{uuid.uuid4().hex[:6].upper()}",
                aircraft_id=aircraft_id,
                start_time="next_scheduled",
                end_time="+24h",
                maintenance_type="Preventive",
                resource_availability={"technicians": 1},
                operational_impact="Reduced",
            ))
        else:
            windows.append(MaintenanceWindow(
                window_id=f"MW-{uuid.uuid4().hex[:6].upper()}",
                aircraft_id=aircraft_id,
                start_time="next_cycle",
                end_time="+8h",
                maintenance_type="Routine",
                resource_availability={"technicians": 1},
                operational_impact="Minimal",
            ))

        return windows

    def what_if_analysis(
        self,
        base_schedule: FleetSchedule,
        scenario: dict,
    ) -> dict:
        scenario_type = scenario.get("type", "")
        impact: dict = {"scenario": scenario_type, "feasible": True}

        if scenario_type == "aircraft_grounding":
            grounded = scenario.get("aircraft_ids", [])
            remaining_operational = base_schedule.total_operational_aircraft - len(grounded)
            impact["remaining_operational"] = remaining_operational
            impact["feasible"] = remaining_operational >= len(scenario.get("min_required", 1))

        elif scenario_type == "route_change":
            impact["rerouted_aircraft"] = len(scenario.get("new_routes", []))
            impact["feasible"] = base_schedule.total_operational_aircraft >= len(scenario.get("new_routes", []))

        elif scenario_type == "fleet_expansion":
            new_count = scenario.get("new_aircraft_count", 0)
            impact["new_total"] = base_schedule.total_operational_aircraft + new_count
            impact["feasible"] = True

        return impact

    def optimize_fleet_resources(
        self,
        aircraft_health: dict[str, dict],
        resource_pool: dict,
    ) -> dict:
        allocation: dict[str, dict] = {}
        total_technicians = resource_pool.get("technicians", 10)
        total_parts = resource_pool.get("spare_parts", 50)

        used_technicians = 0
        used_parts = 0

        for aircraft_id, health in sorted(
            aircraft_health.items(),
            key=lambda x: x[1].get("rul_hours", 10000),
        ):
            rul = health.get("rul_hours", 10000.0)
            if rul < 200:
                needed_tech = 2
                needed_parts = 5
            elif rul < 1000:
                needed_tech = 1
                needed_parts = 2
            else:
                needed_tech = 0
                needed_parts = 0

            if used_technicians + needed_tech <= total_technicians and used_parts + needed_parts <= total_parts:
                allocation[aircraft_id] = {
                    "technicians": needed_tech,
                    "spare_parts": needed_parts,
                }
                used_technicians += needed_tech
                used_parts += needed_parts
            else:
                allocation[aircraft_id] = {
                    "technicians": 0,
                    "spare_parts": 0,
                    "deferred": True,
                }

        return {
            "allocation": allocation,
            "total_technicians_used": used_technicians,
            "total_parts_used": used_parts,
            "remaining_technicians": total_technicians - used_technicians,
            "remaining_parts": total_parts - used_parts,
        }

    def _compute_schedule_score(
        self,
        aircraft_health: dict[str, dict],
        assignments: dict[str, str],
        violations: list[dict],
    ) -> float:
        total = len(aircraft_health)
        if total == 0:
            return 0.0

        operational = sum(1 for a in assignments.values() if a != "grounded")
        availability = operational / total

        violation_penalty = len(violations) * 0.1

        return max(0.0, min(1.0, availability - violation_penalty))