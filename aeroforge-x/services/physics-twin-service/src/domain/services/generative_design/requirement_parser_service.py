"""AeroForge-X v5.0 RequirementParserService

Parses natural language aircraft design requirements into structured DesignRequirement,
validates physical feasibility, and generates conflict reports.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class FeasibilityStatus(str, Enum):
    PENDING = "Pending"
    FEASIBLE = "Feasible"
    INFEASIBLE = "Infeasible"
    PARTIAL = "Partial"


class ConstraintType(str, Enum):
    WING_LOADING = "WingLoading"
    THRUST_TO_WEIGHT = "ThrustToWeight"
    RANGE_PAYLOAD = "RangePayload"
    STRUCTURAL = "Structural"
    PERFORMANCE = "Performance"
    CUSTOM = "Custom"


class ObjectiveDirection(str, Enum):
    MINIMIZE = "Minimize"
    MAXIMIZE = "Maximize"


@dataclass(frozen=True)
class DesignConstraint:
    constraint_name: str
    constraint_type: ConstraintType
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    target_value: Optional[float] = None
    unit: str = ""
    source: str = ""


@dataclass(frozen=True)
class ObjectiveFunction:
    objective_name: str
    direction: ObjectiveDirection
    weight: float = 1.0
    discipline: str = ""
    expression: str = ""


@dataclass(frozen=True)
class PhysicalConstraintLibrary:
    constraint_id: str
    category: str
    description: str
    check_function: str
    parameters: dict = field(default_factory=dict)


@dataclass(frozen=True)
class FeasibilityCheck:
    is_feasible: bool
    violated_constraints: list[str]
    suggested_adjustments: dict[str, float]


@dataclass(frozen=True)
class ConflictReport:
    requirement_id: str
    conflicts: list[dict]
    resolution_suggestions: list[str]


@dataclass
class DesignRequirement:
    requirement_id: str
    version: int
    requirement_text: str
    range_km: Optional[float] = None
    payload_kg: Optional[float] = None
    cruise_speed_kmh: Optional[float] = None
    ceiling_m: Optional[float] = None
    cost_target: Optional[float] = None
    constraints: list[DesignConstraint] = field(default_factory=list)
    objective_functions: list[ObjectiveFunction] = field(default_factory=list)
    feasibility_status: FeasibilityStatus = FeasibilityStatus.PENDING
    conflict_report: Optional[ConflictReport] = None
    project_id: str = ""

    def to_dict(self) -> dict:
        return {
            "requirement_id": self.requirement_id,
            "version": self.version,
            "requirement_text": self.requirement_text,
            "range_km": self.range_km,
            "payload_kg": self.payload_kg,
            "cruise_speed_kmh": self.cruise_speed_kmh,
            "ceiling_m": self.ceiling_m,
            "cost_target": self.cost_target,
            "feasibility_status": self.feasibility_status.value,
            "project_id": self.project_id,
        }


_PHYSICAL_CONSTRAINTS: list[PhysicalConstraintLibrary] = [
    PhysicalConstraintLibrary(
        constraint_id="PC-001",
        category="WingLoading",
        description="Wing loading must be between 100 and 800 kg/m² for conventional aircraft",
        check_function="check_wing_loading",
        parameters={"min_wing_loading": 100.0, "max_wing_loading": 800.0},
    ),
    PhysicalConstraintLibrary(
        constraint_id="PC-002",
        category="ThrustToWeight",
        description="Thrust-to-weight ratio must be between 0.2 and 1.5",
        check_function="check_thrust_to_weight",
        parameters={"min_twr": 0.2, "max_twr": 1.5},
    ),
    PhysicalConstraintLibrary(
        constraint_id="PC-003",
        category="RangePayload",
        description="Range-payload product must satisfy Breguet range equation constraints",
        check_function="check_range_payload",
        parameters={"min_range_km": 100.0, "max_range_km": 20000.0, "min_payload_kg": 10.0},
    ),
    PhysicalConstraintLibrary(
        constraint_id="PC-004",
        category="Performance",
        description="Cruise speed must be below Mach 0.95 for subsonic transport",
        check_function="check_cruise_speed",
        parameters={"max_mach": 0.95, "speed_of_sound_kmh": 1235.0},
    ),
    PhysicalConstraintLibrary(
        constraint_id="PC-005",
        category="Structural",
        description="Ceiling must not exceed 20,000m for conventional aluminum structures",
        check_function="check_ceiling",
        parameters={"max_ceiling_m": 20000.0},
    ),
]

_RANGE_PATTERN = re.compile(
    r"(?:航程|range|飞行距离|航飞距离)\s*[：:>=~约]?\s*(\d+(?:\.\d+)?)\s*(km|千米|公里)",
    re.IGNORECASE,
)
_PAYLOAD_PATTERN = re.compile(
    r"(?:载荷|payload|载重|有效载荷)\s*[：:>=~约]?\s*(\d+(?:\.\d+)?)\s*(kg|千克|公斤|吨|t)",
    re.IGNORECASE,
)
_SPEED_PATTERN = re.compile(
    r"(?:巡航速度|cruise\s*speed|巡航马赫数)\s*[：:>=~约]?\s*(\d+(?:\.\d+)?)\s*(km/?h|马赫|mach)",
    re.IGNORECASE,
)
_CEILING_PATTERN = re.compile(
    r"(?:升限|ceiling|实用升限|飞行高度)\s*[：:>=~约]?\s*(\d+(?:\.\d+)?)\s*(m|米|km|千米)",
    re.IGNORECASE,
)
_COST_PATTERN = re.compile(
    r"(?:成本|cost|造价|目标成本)\s*[：:>=~约]?\s*(\d+(?:\.\d+)?)\s*(万?美元?|万?欧元?|万?元|million|USD|EUR|CNY)",
    re.IGNORECASE,
)


class RequirementParserService:

    def __init__(self) -> None:
        self._requirements: dict[str, DesignRequirement] = {}
        self._physical_constraints = list(_PHYSICAL_CONSTRAINTS)

    def parse_requirement(self, text: str, project_id: str = "") -> DesignRequirement:
        range_km = self._extract_range(text)
        payload_kg = self._extract_payload(text)
        cruise_speed_kmh = self._extract_cruise_speed(text)
        ceiling_m = self._extract_ceiling(text)
        cost_target = self._extract_cost(text)

        constraints = self._infer_constraints(range_km, payload_kg, cruise_speed_kmh, ceiling_m)
        objective_functions = self._infer_objectives(range_km, payload_kg, cruise_speed_kmh, cost_target)

        req_id = f"REQ-{project_id or 'GEN'}-{uuid.uuid4().hex[:8].upper()}"
        requirement = DesignRequirement(
            requirement_id=req_id,
            version=1,
            requirement_text=text,
            range_km=range_km,
            payload_kg=payload_kg,
            cruise_speed_kmh=cruise_speed_kmh,
            ceiling_m=ceiling_m,
            cost_target=cost_target,
            constraints=constraints,
            objective_functions=objective_functions,
            feasibility_status=FeasibilityStatus.PENDING,
            project_id=project_id,
        )

        self._requirements[req_id] = requirement
        return requirement

    def validate_physical_feasibility(self, requirement: DesignRequirement) -> FeasibilityCheck:
        violated: list[str] = []
        adjustments: dict[str, float] = {}

        if requirement.range_km is not None and requirement.payload_kg is not None:
            if requirement.range_km < 100 or requirement.range_km > 20000:
                violated.append("PC-003")
                clamped = max(100.0, min(20000.0, requirement.range_km))
                adjustments["range_km"] = clamped
            if requirement.payload_kg < 10:
                violated.append("PC-003")
                adjustments["payload_kg"] = 10.0

        if requirement.cruise_speed_kmh is not None:
            max_speed = 0.95 * 1235.0
            if requirement.cruise_speed_kmh > max_speed:
                violated.append("PC-004")
                adjustments["cruise_speed_kmh"] = max_speed

        if requirement.ceiling_m is not None:
            if requirement.ceiling_m > 20000:
                violated.append("PC-005")
                adjustments["ceiling_m"] = 20000.0

        is_feasible = len(violated) == 0
        if requirement.requirement_id in self._requirements:
            req = self._requirements[requirement.requirement_id]
            if is_feasible:
                req.feasibility_status = FeasibilityStatus.FEASIBLE
            elif len(violated) < len(self._physical_constraints):
                req.feasibility_status = FeasibilityStatus.PARTIAL
            else:
                req.feasibility_status = FeasibilityStatus.INFEASIBLE

        return FeasibilityCheck(
            is_feasible=is_feasible,
            violated_constraints=violated,
            suggested_adjustments=adjustments,
        )

    def generate_conflict_report(self, requirement: DesignRequirement) -> ConflictReport:
        conflicts: list[dict] = []
        suggestions: list[str] = []

        if requirement.range_km is not None and requirement.payload_kg is not None:
            range_payload_product = requirement.range_km * requirement.payload_kg
            if range_payload_product > 5e7:
                conflicts.append({
                    "parameters": ["range_km", "payload_kg"],
                    "constraint": "Range-payload product exceeds feasible limit",
                    "values": {
                        "range_km": requirement.range_km,
                        "payload_kg": requirement.payload_kg,
                        "product": range_payload_product,
                    },
                })
                suggestions.append("Reduce range or payload to bring range-payload product below 5e7")

        if requirement.cruise_speed_kmh is not None and requirement.ceiling_m is not None:
            if requirement.cruise_speed_kmh > 1000 and requirement.ceiling_m > 15000:
                conflicts.append({
                    "parameters": ["cruise_speed_kmh", "ceiling_m"],
                    "constraint": "High speed + high ceiling may require pressurization beyond structural limits",
                    "values": {
                        "cruise_speed_kmh": requirement.cruise_speed_kmh,
                        "ceiling_m": requirement.ceiling_m,
                    },
                })
                suggestions.append("Consider reducing ceiling or speed for conventional aluminum structure")

        report = ConflictReport(
            requirement_id=requirement.requirement_id,
            conflicts=conflicts,
            resolution_suggestions=suggestions,
        )

        if requirement.requirement_id in self._requirements:
            self._requirements[requirement.requirement_id].conflict_report = report

        return report

    def get_requirement_version(self, requirement_id: str, version: int | None = None) -> Optional[DesignRequirement]:
        req = self._requirements.get(requirement_id)
        if req is None:
            return None
        if version is not None and req.version != version:
            return None
        return req

    def _extract_range(self, text: str) -> Optional[float]:
        m = _RANGE_PATTERN.search(text)
        if m:
            value = float(m.group(1))
            return value
        return None

    def _extract_payload(self, text: str) -> Optional[float]:
        m = _PAYLOAD_PATTERN.search(text)
        if m:
            value = float(m.group(1))
            unit = m.group(2).lower()
            if unit in ("吨", "t"):
                value *= 1000.0
            return value
        return None

    def _extract_cruise_speed(self, text: str) -> Optional[float]:
        m = _SPEED_PATTERN.search(text)
        if m:
            value = float(m.group(1))
            unit = m.group(2).lower()
            if unit in ("马赫", "mach"):
                value *= 1235.0
            return value
        return None

    def _extract_ceiling(self, text: str) -> Optional[float]:
        m = _CEILING_PATTERN.search(text)
        if m:
            value = float(m.group(1))
            unit = m.group(2).lower()
            if unit in ("km", "千米"):
                value *= 1000.0
            return value
        return None

    def _extract_cost(self, text: str) -> Optional[float]:
        m = _COST_PATTERN.search(text)
        if m:
            value = float(m.group(1))
            unit = m.group(2).lower()
            if "万" in unit or "million" in unit:
                value *= 1e6
            return value
        return None

    def _infer_constraints(
        self,
        range_km: Optional[float],
        payload_kg: Optional[float],
        cruise_speed_kmh: Optional[float],
        ceiling_m: Optional[float],
    ) -> list[DesignConstraint]:
        constraints: list[DesignConstraint] = []

        if range_km is not None:
            constraints.append(DesignConstraint(
                constraint_name="min_range",
                constraint_type=ConstraintType.RANGE_PAYLOAD,
                lower_bound=range_km * 0.9,
                upper_bound=None,
                unit="km",
                source="extracted",
            ))

        if payload_kg is not None:
            constraints.append(DesignConstraint(
                constraint_name="min_payload",
                constraint_type=ConstraintType.RANGE_PAYLOAD,
                lower_bound=payload_kg * 0.95,
                upper_bound=None,
                unit="kg",
                source="extracted",
            ))

        if cruise_speed_kmh is not None:
            constraints.append(DesignConstraint(
                constraint_name="cruise_speed",
                constraint_type=ConstraintType.PERFORMANCE,
                lower_bound=cruise_speed_kmh * 0.95,
                upper_bound=cruise_speed_kmh * 1.05,
                unit="km/h",
                source="extracted",
            ))

        if ceiling_m is not None:
            constraints.append(DesignConstraint(
                constraint_name="min_ceiling",
                constraint_type=ConstraintType.STRUCTURAL,
                lower_bound=ceiling_m * 0.9,
                upper_bound=None,
                unit="m",
                source="extracted",
            ))

        return constraints

    def _infer_objectives(
        self,
        range_km: Optional[float],
        payload_kg: Optional[float],
        cruise_speed_kmh: Optional[float],
        cost_target: Optional[float],
    ) -> list[ObjectiveFunction]:
        objectives: list[ObjectiveFunction] = []

        if range_km is not None:
            objectives.append(ObjectiveFunction(
                objective_name="maximize_range",
                direction=ObjectiveDirection.MAXIMIZE,
                weight=1.0,
                discipline="Performance",
                expression="range_km",
            ))

        if payload_kg is not None:
            objectives.append(ObjectiveFunction(
                objective_name="maximize_payload",
                direction=ObjectiveDirection.MAXIMIZE,
                weight=1.0,
                discipline="Performance",
                expression="payload_kg",
            ))

        objectives.append(ObjectiveFunction(
            objective_name="minimize_weight",
            direction=ObjectiveDirection.MINIMIZE,
            weight=1.0,
            discipline="Structure",
            expression="mtow_kg",
        ))

        if cost_target is not None:
            objectives.append(ObjectiveFunction(
                objective_name="minimize_cost",
                direction=ObjectiveDirection.MINIMIZE,
                weight=0.5,
                discipline="Economics",
                expression="total_cost",
            ))

        return objectives