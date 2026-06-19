from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class TestPoint:
    def __init__(self, point_id: str, test_point_number: int, name: str, objective: str, conditions: dict[str, Any]):
        self.point_id = point_id
        self.test_point_number = test_point_number
        self.name = name
        self.objective = objective
        self.conditions = conditions
        self.safety_boundaries: dict[str, Any] = {}
        self.emergency_procedures: list[str] = []
        self.within_flight_envelope: bool = True
        self.certification_requirement_refs: list[str] = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "point_id": self.point_id,
            "test_point_number": self.test_point_number,
            "name": self.name,
            "objective": self.objective,
            "conditions": self.conditions,
            "safety_boundaries": self.safety_boundaries,
            "emergency_procedures": self.emergency_procedures,
            "within_flight_envelope": self.within_flight_envelope,
            "certification_requirement_refs": self.certification_requirement_refs,
        }


class FlightTestSortie:
    def __init__(self, sortie_id: str, sortie_number: int, subject: str):
        self.sortie_id = sortie_id
        self.sortie_number = sortie_number
        self.subject = subject
        self.test_points: list[TestPoint] = []
        "estimated_duration_hours": float = 2.0
        self.configuration: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "sortie_id": self.sortie_id,
            "sortie_number": self.sortie_number,
            "subject": self.subject,
            "test_points": [tp.to_dict() for tp in self.test_points],
            "estimated_duration_hours": self.estimated_duration_hours,
            "configuration": self.configuration,
        }


class FlightTestPlan:
    def __init__(self, plan_id: str, aircraft_type: str):
        self.plan_id = plan_id
        self.aircraft_type = aircraft_type
        self.sorties: list[FlightTestSortie] = []
        self.certification_coverage: dict[str, float] = {}
        self.uncovered_requirements: list[str] = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "aircraft_type": self.aircraft_type,
            "sorties": [s.to_dict() for s in self.sorties],
            "certification_coverage": self.certification_coverage,
            "uncovered_requirements": self.uncovered_requirements,
            "total_sorties": len(self.sorties),
            "total_test_points": sum(len(s.test_points) for s in self.sorties),
        }


FLIGHT_ENVELOPE = {
    "altitude_ft": {"min": 0, "max": 43000},
    "airspeed_kts": {"min": 120, "max": 350},
    "mach": {"min": 0.0, "max": 0.89},
    "g_load": {"min": -1.0, "max": 3.5},
    "aoa_deg": {"min": -5.0, "max": 25.0},
}


class AeroGPTTestPilot:
    def __init__(self, event_publisher: Any | None = None):
        self._event_publisher = event_publisher
        self._plans: dict[str, FlightTestPlan] = {}

    async def _publish_event(self, subject: str, data: dict[str, Any]) -> None:
        if self._event_publisher:
            await self._event_publisher.publish(subject, data)

    def generate_flight_test_plan(self, aircraft_type: str, certification_requirements: list[str] | None = None, flight_envelope: dict[str, Any] | None = None) -> FlightTestPlan:
        plan = FlightTestPlan(plan_id=str(uuid4()), aircraft_type=aircraft_type)
        envelope = flight_envelope or FLIGHT_ENVELOPE
        cert_reqs = certification_requirements or []

        sortie_defs = [
            {
                "subject": "Envelope Exploration",
                "points": [
                    {"name": "Initial Flutter Clearance", "objective": "Verify no flutter within operational envelope", "conditions": {"altitude_ft": 25000, "airspeed_kts": 280, "mach": 0.75}, "cert_refs": ["25.629"]},
                    {"name": "VMO/MMO Demonstration", "objective": "Demonstrate maximum operating speed", "conditions": {"altitude_ft": 20000, "airspeed_kts": 330, "mach": 0.87}, "cert_refs": ["25.1505"]},
                    {"name": "High Altitude Performance", "objective": "Verify performance at maximum altitude", "conditions": {"altitude_ft": 41000, "airspeed_kts": 250, "mach": 0.80}, "cert_refs": ["25.1527"]},
                ],
            },
            {
                "subject": "Stability and Control",
                "points": [
                    {"name": "Longitudinal Static Stability", "objective": "Verify positive longitudinal stability", "conditions": {"altitude_ft": 15000, "airspeed_kts": 250, "cg_position": "forward"}, "cert_refs": ["25.173"]},
                    {"name": "Lateral-Directional Stability", "objective": "Verify lateral-directional stability characteristics", "conditions": {"altitude_ft": 15000, "airspeed_kts": 250}, "cert_refs": ["25.177"]},
                    {"name": "Stall Characteristics", "objective": "Demonstrate acceptable stall characteristics", "conditions": {"altitude_ft": 10000, "airspeed_kts": 130, "aoa_deg": 22}, "cert_refs": ["25.201", "25.203"]},
                ],
            },
            {
                "subject": "Structural Loads",
                "points": [
                    {"name": "Maneuver Loads - 2.5g Pull-up", "objective": "Verify structural loads at limit maneuver", "conditions": {"altitude_ft": 15000, "airspeed_kts": 280, "g_load": 2.5}, "cert_refs": ["25.337"]},
                    {"name": "Gust Response", "objective": "Verify gust loads within design limits", "conditions": {"altitude_ft": 20000, "airspeed_kts": 300}, "cert_refs": ["25.341"]},
                    {"name": "Landing Loads", "objective": "Verify landing loads at design sink rate", "conditions": {"altitude_ft": 0, "sink_rate_fpm": 360}, "cert_refs": ["25.473"]},
                ],
            },
            {
                "subject": "Systems Verification",
                "points": [
                    {"name": "Engine In-Flight Restart", "objective": "Demonstrate engine relight capability", "conditions": {"altitude_ft": 25000, "airspeed_kts": 250}, "cert_refs": ["25.903"]},
                    {"name": "Hydraulic System Failure", "objective": "Verify flight controls with hydraulic failure", "conditions": {"altitude_ft": 20000, "airspeed_kts": 250}, "cert_refs": ["25.1435"]},
                    {"name": "Electrical System Emergency", "objective": "Verify emergency electrical configuration", "conditions": {"altitude_ft": 20000, "airspeed_kts": 250}, "cert_refs": ["25.1351"]},
                ],
            },
        ]

        for sortie_idx, sortie_def in enumerate(sortie_defs):
            sortie = FlightTestSortie(sortie_id=str(uuid4()), sortie_number=sortie_idx + 1, subject=sortie_def["subject"])
            for pt_idx, pt_def in enumerate(sortie_def["points"]):
                tp = TestPoint(
                    point_id=f"TP-{sortie_idx + 1}-{pt_idx + 1:03d}",
                    test_point_number=pt_idx + 1,
                    name=pt_def["name"],
                    objective=pt_def["objective"],
                    conditions=pt_def["conditions"],
                )
                tp.certification_requirement_refs = pt_def.get("cert_refs", [])
                tp.within_flight_envelope = self._check_envelope(pt_def["conditions"], envelope)
                tp.safety_boundaries = self._generate_safety_boundaries(pt_def["conditions"], envelope)
                tp.emergency_procedures = self._generate_emergency_procedures(pt_def["name"])
                sortie.test_points.append(tp)
            plan.sorties.append(sortie)

        self._check_certification_coverage(plan, cert_reqs)
        self._plans[plan.plan_id] = plan
        return plan

    def _check_envelope(self, conditions: dict[str, Any], envelope: dict[str, Any]) -> bool:
        for param, limits in envelope.items():
            key = param
            if key in conditions:
                value = conditions[key]
                if isinstance(limits, dict):
                    if "min" in limits and value < limits["min"]:
                        return False
                    if "max" in limits and value > limits["max"]:
                        return False
        return True

    def _generate_safety_boundaries(self, conditions: dict[str, Any], envelope: dict[str, Any]) -> dict[str, Any]:
        boundaries = {}
        for param, limits in envelope.items():
            if param in conditions:
                if isinstance(limits, dict):
                    boundaries[param] = {
                        "test_value": conditions[param],
                        "limit_min": limits.get("min"),
                        "limit_max": limits.get("max"),
                        "margin": min(
                            conditions[param] - limits["min"] if limits.get("min") is not None else float('inf'),
                            limits["max"] - conditions[param] if limits.get("max") is not None else float('inf'),
                        ),
                    }
        return boundaries

    def _generate_emergency_procedures(self, test_name: str) -> list[str]:
        procedures = [
            "If abnormal vibration detected, reduce airspeed and altitude immediately",
            "If structural limit exceeded, recover to 1g flight and land as soon as practicable",
        ]
        if "stall" in test_name.lower():
            procedures.append("If uncommanded roll or yaw occurs during stall, apply standard stall recovery")
        if "engine" in test_name.lower():
            procedures.append("If engine fails to restart, proceed to nearest suitable airport on remaining engine(s)")
        if "hydraulic" in test_name.lower():
            procedures.append("If manual reversion is inadequate, declare emergency and land at nearest suitable airport")
        return procedures

    def _check_certification_coverage(self, plan: FlightTestPlan, cert_reqs: list[str]) -> None:
        covered: set[str] = set()
        for sortie in plan.sorties:
            for tp in sortie.test_points:
                for ref in tp.certification_requirement_refs:
                    covered.add(ref)

        uncovered = [r for r in cert_reqs if r not in covered]
        plan.uncovered_requirements = uncovered

        if cert_reqs:
            coverage_pct = len(covered & set(cert_reqs)) / len(cert_reqs) * 100
            plan.certification_coverage = {
                "total_requirements": len(cert_reqs),
                "covered": len(covered & set(cert_reqs)),
                "uncovered": len(uncovered),
                "coverage_percentage": round(coverage_pct, 1),
            }

    def get_plan(self, plan_id: str) -> FlightTestPlan | None:
        return self._plans.get(plan_id)