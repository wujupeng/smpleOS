from __future__ import annotations

import logging
import re
from typing import Any
from uuid import uuid4

from src.domain.entities.ai_proposal import AIProposal, FeasibilityReport, ProposalStatus, RiskMarker, RiskSeverity

logger = logging.getLogger(__name__)


class ClarificationQuestion:
    def __init__(self, question_id: str, question: str, reason: str, suggested_answers: list[str] | None = None):
        self.question_id = question_id
        self.question = question
        self.reason = reason
        self.suggested_answers = suggested_answers or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "question_id": self.question_id,
            "question": self.question,
            "reason": self.reason,
            "suggested_answers": self.suggested_answers,
        }


class DesignRule:
    def __init__(self, rule_id: str, name: str, category: str, min_value: float | None = None, max_value: float | None = None, required: bool = True):
        self.rule_id = rule_id
        self.name = name
        self.category = category
        self.min_value = min_value
        self.max_value = max_value
        self.required = required

    def check(self, value: float) -> dict[str, Any] | None:
        if self.min_value is not None and value < self.min_value:
            return {"rule_id": self.rule_id, "name": self.name, "violation": f"Value {value} below minimum {self.min_value}"}
        if self.max_value is not None and value > self.max_value:
            return {"rule_id": self.rule_id, "name": self.name, "violation": f"Value {value} above maximum {self.max_value}"}
        return None


DEFAULT_DESIGN_RULES = [
    DesignRule("DR-001", "Wingspan Range", "geometry", min_value=10.0, max_value=80.0),
    DesignRule("DR-002", "Fuselage Length Range", "geometry", min_value=15.0, max_value=90.0),
    DesignRule("DR-003", "MTOW Range", "performance", min_value=5000.0, max_value=650000.0),
    DesignRule("DR-004", "Cruise Speed Range", "performance", min_value=100.0, max_value=620.0),
    DesignRule("DR-005", "Range Minimum", "performance", min_value=500.0),
    DesignRule("DR-006", "Crew Minimum", "crew", min_value=2),
    DesignRule("DR-007", "Passenger Max", "capacity", max_value=850.0),
]

AIRCRAFT_TYPE_PATTERNS = {
    "narrow_body": ["narrow", "single aisle", "a320", "b737", "regional"],
    "wide_body": ["wide", "twin aisle", "a350", "b777", "b787", "long haul"],
    "regional": ["regional", "turboprop", "short haul", "commuter"],
    "business": ["business", "private", "executive", "corporate"],
    "cargo": ["cargo", "freighter", "freight"],
}


class AeroGPTDesigner:
    def __init__(self, event_publisher: Any | None = None):
        self._event_publisher = event_publisher
        self._design_rules = list(DEFAULT_DESIGN_RULES)
        self._proposals: dict[str, AIProposal] = {}

    async def _publish_event(self, subject: str, data: dict[str, Any]) -> None:
        if self._event_publisher:
            await self._event_publisher.publish(subject, data)

    def parse_natural_language(self, description: str) -> dict[str, Any]:
        parsed = {
            "aircraft_type": self._detect_aircraft_type(description),
            "parameters": {},
            "missing_fields": [],
            "ambiguities": [],
        }

        wingspan = self._extract_numeric(description, ["wingspan", "span"])
        if wingspan is not None:
            parsed["parameters"]["wingspan_m"] = wingspan

        length = self._extract_numeric(description, ["length", "fuselage length"])
        if length is not None:
            parsed["parameters"]["fuselage_length_m"] = length

        mtow = self._extract_numeric(description, ["mtow", "maximum takeoff weight", "takeoff weight"])
        if mtow is not None:
            parsed["parameters"]["mtow_kg"] = mtow

        speed = self._extract_numeric(description, ["cruise speed", "speed", "mach"])
        if speed is not None:
            parsed["parameters"]["cruise_speed_kts"] = speed

        range_val = self._extract_numeric(description, ["range", "flight range"])
        if range_val is not None:
            parsed["parameters"]["range_nm"] = range_val

        pax = self._extract_numeric(description, ["passenger", "pax", "seats"])
        if pax is not None:
            parsed["parameters"]["passenger_count"] = pax

        required_fields = ["wingspan_m", "fuselage_length_m", "mtow_kg", "cruise_speed_kts"]
        for field in required_fields:
            if field not in parsed["parameters"]:
                parsed["missing_fields"].append(field)

        if "approximately" in description.lower() or "around" in description.lower() or "about" in description.lower():
            parsed["ambiguities"].append("approximate_values")

        return parsed

    def generate_aircraft_spec(self, description: str, project_id: str = "", created_by: str = "") -> AIProposal:
        parsed = self.parse_natural_language(description)
        proposal = AIProposal(
            project_id=project_id,
            natural_language_input=description,
            parsed_spec=parsed["parameters"],
            created_by=created_by,
        )

        if parsed["missing_fields"] or parsed["ambiguities"]:
            questions = self._generate_clarification_questions(parsed)
            proposal.clarification_questions = [q.question for q in questions]

        feasibility = self._assess_feasibility(parsed["parameters"])
        proposal.feasibility_report = feasibility

        if not feasibility.is_feasible:
            for violation in feasibility.design_rule_violations:
                proposal.risk_markers.append(RiskMarker(
                    marker_id=f"RM-{len(proposal.risk_markers) + 1:03d}",
                    category="design_rule_violation",
                    description=violation.get("violation", ""),
                    severity=RiskSeverity.HIGH,
                    suggestion="Adjust parameter to comply with design rules",
                ))

        proposal.status = ProposalStatus.PENDING_REVIEW
        self._proposals[proposal.id] = proposal
        return proposal

    async def generate_initial_model(self, proposal_id: str) -> dict[str, Any]:
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")

        spec = proposal.parsed_spec
        model = {
            "model_id": str(uuid4()),
            "proposal_id": proposal_id,
            "model_type": "parametric_aircraft",
            "geometry": {
                "wingspan_m": spec.get("wingspan_m", 35.8),
                "fuselage_length_m": spec.get("fuselage_length_m", 40.0),
                "fuselage_diameter_m": spec.get("fuselage_length_m", 40.0) * 0.1 if "fuselage_length_m" in spec else 4.0,
                "wing_area_m2": spec.get("wingspan_m", 35.8) * 6.0,
                "aspect_ratio": 9.0,
                "sweep_angle_deg": 25.0,
            },
            "performance": {
                "mtow_kg": spec.get("mtow_kg", 80000),
                "cruise_speed_kts": spec.get("cruise_speed_kts", 450),
                "range_nm": spec.get("range_nm", 3000),
                "ceiling_ft": 39000,
            },
            "status": "generated",
        }

        proposal.generated_model_ref = model["model_id"]

        await self._publish_event("aerogpt.proposal.generated", {
            "proposal_id": proposal_id,
            "model_id": model["model_id"],
            "agent_type": "designer",
        })
        logger.info(f"Initial model generated for proposal {proposal_id}")
        return model

    def _detect_aircraft_type(self, description: str) -> str:
        desc_lower = description.lower()
        for aircraft_type, patterns in AIRCRAFT_TYPE_PATTERNS.items():
            for pattern in patterns:
                if pattern in desc_lower:
                    return aircraft_type
        return "unknown"

    def _extract_numeric(self, text: str, keywords: list[str]) -> float | None:
        text_lower = text.lower()
        for keyword in keywords:
            pattern = rf"{keyword}\s*(?:of|is|:)?\s*(\d+\.?\d*)"
            match = re.search(pattern, text_lower)
            if match:
                return float(match.group(1))
        return None

    def _generate_clarification_questions(self, parsed: dict[str, Any]) -> list[ClarificationQuestion]:
        questions = []
        q_id = 1
        for field in parsed.get("missing_fields", []):
            field_display = field.replace("_", " ").title()
            questions.append(ClarificationQuestion(
                question_id=f"Q-{q_id:03d}",
                question=f"Please specify the {field_display}",
                reason=f"{field_display} is required for aircraft specification",
                suggested_answers=self._get_default_suggestions(field),
            ))
            q_id += 1

        if "approximate_values" in parsed.get("ambiguities", []):
            questions.append(ClarificationQuestion(
                question_id=f"Q-{q_id:03d}",
                question="Some values appear approximate. Would you like to specify exact values?",
                reason="Exact values improve design accuracy",
                suggested_answers=["Use approximate values", "Let me specify exact values"],
            ))
        return questions

    def _get_default_suggestions(self, field: str) -> list[str]:
        defaults = {
            "wingspan_m": ["35.8 (A320)", "64.8 (A350)", "28.9 (Regional)"],
            "fuselage_length_m": ["37.6 (A320)", "66.8 (A350)", "27.0 (Regional)"],
            "mtow_kg": ["78000 (A320)", "280000 (A350)", "30000 (Regional)"],
            "cruise_speed_kts": ["450 (Jet)", "350 (Turboprop)"],
        }
        return defaults.get(field, [])

    def _assess_feasibility(self, parameters: dict[str, Any]) -> FeasibilityReport:
        violations = []
        scores = []

        for rule in self._design_rules:
            param_name = None
            if rule.category == "geometry" and "wingspan" in rule.name.lower():
                param_name = "wingspan_m"
            elif rule.category == "geometry" and "length" in rule.name.lower():
                param_name = "fuselage_length_m"
            elif rule.category == "performance" and "mtow" in rule.name.lower():
                param_name = "mtow_kg"
            elif rule.category == "performance" and "speed" in rule.name.lower():
                param_name = "cruise_speed_kts"
            elif rule.category == "performance" and "range" in rule.name.lower():
                param_name = "range_nm"
            elif rule.category == "crew":
                param_name = "crew_count"
            elif rule.category == "capacity" and "passenger" in rule.name.lower():
                param_name = "passenger_count"

            if param_name and param_name in parameters:
                violation = rule.check(parameters[param_name])
                if violation:
                    violations.append(violation)
                    scores.append(0.0)
                else:
                    scores.append(1.0)

        is_feasible = len(violations) == 0
        overall_score = sum(scores) / len(scores) if scores else 0.5

        return FeasibilityReport(
            is_feasible=is_feasible,
            design_rule_violations=violations,
            overall_score=overall_score,
            summary="All design rules satisfied" if is_feasible else f"{len(violations)} design rule violation(s) found",
        )

    def get_proposal(self, proposal_id: str) -> AIProposal | None:
        return self._proposals.get(proposal_id)

    def list_proposals(self, status: ProposalStatus | None = None) -> list[AIProposal]:
        proposals = list(self._proposals.values())
        if status:
            proposals = [p for p in proposals if p.status == status]
        return proposals