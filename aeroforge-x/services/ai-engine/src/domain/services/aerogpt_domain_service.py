from __future__ import annotations

import logging
import re
from typing import Any

from aeroforge_common.domain.base import DomainEvent

from .entities.ai_proposal import (
    AIProposal, ProposalStatus, FeasibilityReport, RiskMarker, RiskSeverity,
)

logger = logging.getLogger(__name__)

PARAMETER_PATTERNS: list[dict[str, Any]] = [
    {"pattern": r"(\d+(?:\.\d+)?)\s*kg", "param": "payload_kg", "type": "float"},
    {"pattern": r"(\d+(?:\.\d+)?)\s*公里", "param": "range_km", "type": "float"},
    {"pattern": r"(\d+(?:\.\d+)?)\s*km", "param": "range_km", "type": "float"},
    {"pattern": r"(\d+(?:\.\d+)?)\s*千米", "param": "range_km", "type": "float"},
    {"pattern": r"时速\s*(\d+(?:\.\d+)?)", "param": "cruise_speed_kmh", "type": "float"},
    {"pattern": r"(\d+(?:\.\d+)?)\s*km/h", "param": "cruise_speed_kmh", "type": "float"},
    {"pattern": r"(\d+(?:\.\d+)?)\s*公里每小时", "param": "cruise_speed_kmh", "type": "float"},
    {"pattern": r"(\d+(?:\.\d+)?)\s*米", "param": "takeoff_distance_m", "type": "float"},
    {"pattern": r"电动", "param": "power_type", "value": "electric"},
    {"pattern": r"燃油", "param": "power_type", "value": "fuel"},
    {"pattern": r"混合动力", "param": "power_type", "value": "hybrid"},
    {"pattern": r"垂直起降", "param": "vtol", "value": True},
    {"pattern": r"VTOL", "param": "vtol", "value": True},
    {"pattern": r"固定翼", "param": "aircraft_type", "value": "fixed_wing"},
    {"pattern": r"eVTOL", "param": "aircraft_type", "value": "evtol"},
    {"pattern": r"滑翔机", "param": "aircraft_type", "value": "glider"},
    {"pattern": r"无人机", "param": "aircraft_type", "value": "uav"},
    {"pattern": r"载人", "param": "crew", "value": True},
    {"pattern": r"载客\s*(\d+)", "param": "passenger_count", "type": "int"},
    {"pattern": r"(\d+(?:\.\d+)?)\s*人", "param": "passenger_count", "type": "int"},
]

SPEC_VALIDATION_RULES: dict[str, dict[str, Any]] = {
    "payload_kg": {"min": 1, "max": 50000, "label": "载荷"},
    "range_km": {"min": 1, "max": 20000, "label": "航程"},
    "cruise_speed_kmh": {"min": 10, "max": 1000, "label": "巡航速度"},
    "takeoff_distance_m": {"min": 0, "max": 5000, "label": "起飞距离"},
}

SPEED_POWER_CONSTRAINTS: list[dict[str, Any]] = [
    {"power_type": "electric", "max_speed": 350, "label": "电动飞行器巡航速度上限350km/h"},
    {"power_type": "fuel", "max_speed": 900, "label": "燃油飞行器巡航速度上限900km/h"},
]


class AeroGPTDomainService:
    def __init__(self) -> None:
        self._proposals: dict[str, AIProposal] = {}
        self._proposal_counter: int = 0

    def parse_natural_language(self, user_input: str) -> dict[str, Any]:
        parsed: dict[str, Any] = {}
        clarification_questions: list[str] = []

        for rule in PARAMETER_PATTERNS:
            match = re.search(rule["pattern"], user_input, re.IGNORECASE)
            if match:
                if "value" in rule:
                    parsed[rule["param"]] = rule["value"]
                elif "type" in rule and rule["type"] == "float":
                    parsed[rule["param"]] = float(match.group(1))
                elif "type" in rule and rule["type"] == "int":
                    parsed[rule["param"]] = int(match.group(1))

        if "payload_kg" not in parsed:
            clarification_questions.append("请指定载荷重量（kg）")
        if "range_km" not in parsed:
            clarification_questions.append("请指定航程（km）")
        if "cruise_speed_kmh" not in parsed:
            clarification_questions.append("请指定巡航速度（km/h）")
        if "power_type" not in parsed:
            clarification_questions.append("请指定动力类型（电动/燃油/混合动力）")

        if "takeoff_distance_m" not in parsed:
            parsed["takeoff_distance_m"] = 100

        if parsed.get("vtol"):
            parsed["takeoff_distance_m"] = 0

        if parsed.get("aircraft_type") is None:
            if parsed.get("vtol"):
                parsed["aircraft_type"] = "evtol"
            elif parsed.get("cruise_speed_kmh", 0) < 100 and parsed.get("power_type") != "electric":
                parsed["aircraft_type"] = "glider"
            else:
                parsed["aircraft_type"] = "fixed_wing"

        return {
            "parsed_spec": parsed,
            "clarification_questions": clarification_questions,
        }

    def generate_initial_proposal(
        self,
        project_id: str,
        tenant_id: str,
        natural_language_input: str,
        created_by: str = "",
    ) -> AIProposal:
        parse_result = self.parse_natural_language(natural_language_input)
        parsed_spec = parse_result["parsed_spec"]
        clarification_questions = parse_result["clarification_questions"]

        self._proposal_counter += 1
        proposal = AIProposal(
            project_id=project_id,
            tenant_id=tenant_id,
            status=ProposalStatus.PENDING_REVIEW,
            natural_language_input=natural_language_input,
            parsed_spec=parsed_spec,
            clarification_questions=clarification_questions,
            created_by=created_by,
        )

        proposal.generated_model_ref = f"model-{proposal.id[:8]}"

        feasibility = self.evaluate_feasibility(parsed_spec)
        proposal.feasibility_report = feasibility

        risk_markers = self._generate_risk_markers(parsed_spec, feasibility)
        proposal.risk_markers = risk_markers

        self._proposals[proposal.id] = proposal

        proposal.add_domain_event(DomainEvent(
            event_type="ai.proposal.generated",
            aggregate_id=proposal.id,
            payload={"proposal_id": proposal.id, "project_id": project_id},
        ))

        logger.info("Generated AI proposal %s for project %s", proposal.id, project_id)
        return proposal

    def evaluate_feasibility(self, spec: dict[str, Any]) -> FeasibilityReport:
        violations: list[dict[str, Any]] = []
        is_feasible = True
        score = 100.0

        for param, rule in SPEC_VALIDATION_RULES.items():
            value = spec.get(param)
            if value is not None:
                if value < rule["min"] or value > rule["max"]:
                    violations.append({
                        "parameter": param,
                        "value": value,
                        "rule": f"{rule['label']}应在{rule['min']}-{rule['max']}之间",
                        "severity": "error",
                    })
                    is_feasible = False
                    score -= 30

        power_type = spec.get("power_type")
        cruise_speed = spec.get("cruise_speed_kmh", 0)
        for constraint in SPEED_POWER_CONSTRAINTS:
            if power_type == constraint["power_type"] and cruise_speed > constraint["max_speed"]:
                violations.append({
                    "parameter": "cruise_speed_kmh",
                    "value": cruise_speed,
                    "rule": constraint["label"],
                    "severity": "warning",
                })
                score -= 15

        if spec.get("payload_kg", 0) > 500 and spec.get("range_km", 0) > 1000 and power_type == "electric":
            violations.append({
                "parameter": "payload_range_product",
                "value": f"{spec.get('payload_kg')}kg * {spec.get('range_km')}km",
                "rule": "大载荷+长航程+电动组合可能不可行",
                "severity": "warning",
            })
            score -= 10

        cae_assessment = self._quick_cae_assessment(spec)

        parameter_rationality = self._assess_parameter_rationality(spec)

        score = max(0, score)
        summary = "方案可行" if is_feasible and score >= 60 else "方案存在风险，建议调整" if score >= 30 else "方案不可行"

        return FeasibilityReport(
            is_feasible=is_feasible,
            design_rule_violations=violations,
            cae_assessment=cae_assessment,
            parameter_rationality=parameter_rationality,
            overall_score=score,
            summary=summary,
        )

    def iterate_with_feedback(
        self,
        proposal_id: str,
        feedback: str,
        param_adjustments: dict[str, Any] | None = None,
    ) -> AIProposal | None:
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            return None

        adjustments = param_adjustments or self._parse_feedback_to_adjustments(feedback, proposal.parsed_spec)

        proposal.add_iteration(feedback, adjustments)

        feasibility = self.evaluate_feasibility(proposal.parsed_spec)
        proposal.feasibility_report = feasibility

        risk_markers = self._generate_risk_markers(proposal.parsed_spec, feasibility)
        proposal.risk_markers = risk_markers

        return proposal

    def confirm_proposal(self, proposal_id: str) -> AIProposal | None:
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            return None
        proposal.confirm()
        return proposal

    def reject_proposal(self, proposal_id: str, reason: str = "") -> AIProposal | None:
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            return None
        proposal.reject(reason)
        return proposal

    def get_proposal(self, proposal_id: str) -> AIProposal | None:
        return self._proposals.get(proposal_id)

    def list_proposals(self, project_id: str | None = None) -> list[AIProposal]:
        proposals = list(self._proposals.values())
        if project_id:
            proposals = [p for p in proposals if p.project_id == project_id]
        return proposals

    def _quick_cae_assessment(self, spec: dict[str, Any]) -> dict[str, Any]:
        wing_span = spec.get("wing_span", 15.0)
        payload = spec.get("payload_kg", 100)
        speed = spec.get("cruise_speed_kmh", 120)

        wing_loading = payload / max(wing_span, 1)
        estimated_lift_coeff = min(2.0, wing_loading / 500)

        return {
            "wing_loading_estimate": round(wing_loading, 2),
            "estimated_lift_coefficient": round(estimated_lift_coeff, 3),
            "structural_feasibility": "likely" if wing_loading < 50 else "challenging",
            "aerodynamic_efficiency": "good" if speed < 200 else "requires_optimization",
        }

    def _assess_parameter_rationality(self, spec: dict[str, Any]) -> dict[str, Any]:
        payload = spec.get("payload_kg", 0)
        range_km = spec.get("range_km", 0)
        speed = spec.get("cruise_speed_kmh", 0)

        payload_range_product = payload * range_km
        battery_energy_estimate = payload_range_product * 0.5 if spec.get("power_type") == "electric" else 0

        return {
            "payload_range_product": payload_range_product,
            "battery_energy_estimate_kwh": round(battery_energy_estimate, 1),
            "complexity_level": "high" if payload_range_product > 100000 else "medium" if payload_range_product > 10000 else "low",
        }

    def _generate_risk_markers(self, spec: dict[str, Any], feasibility: FeasibilityReport) -> list[RiskMarker]:
        markers: list[RiskMarker] = []

        for violation in feasibility.design_rule_violations:
            severity = RiskSeverity.CRITICAL if violation.get("severity") == "error" else RiskSeverity.HIGH
            markers.append(RiskMarker(
                marker_id=f"RISK-{len(markers) + 1:03d}",
                category="design_rule_violation",
                description=violation.get("rule", "Unknown violation"),
                severity=severity,
                suggestion="请调整参数至合理范围",
            ))

        if not feasibility.is_feasible:
            markers.append(RiskMarker(
                marker_id=f"RISK-{len(markers) + 1:03d}",
                category="feasibility",
                description="方案可行性评估未通过",
                severity=RiskSeverity.CRITICAL,
                suggestion="建议降低载荷或航程要求",
            ))

        if spec.get("power_type") == "electric" and spec.get("range_km", 0) > 500:
            markers.append(RiskMarker(
                marker_id=f"RISK-{len(markers) + 1:03d}",
                category="technology_risk",
                description="电动飞行器航程超过500km，电池技术风险较高",
                severity=RiskSeverity.MEDIUM,
                suggestion="考虑混合动力方案或降低航程要求",
            ))

        return markers

    def _parse_feedback_to_adjustments(self, feedback: str, current_spec: dict[str, Any]) -> dict[str, Any]:
        adjustments: dict[str, Any] = {}

        increase_match = re.search(r"增加.*?(\d+(?:\.\d+)?)", feedback)
        decrease_match = re.search(r"减少.*?(\d+(?:\.\d+)?)", feedback)

        if "载荷" in feedback or "载重" in feedback:
            if increase_match:
                adjustments["payload_kg"] = current_spec.get("payload_kg", 100) + float(increase_match.group(1))
            elif decrease_match:
                adjustments["payload_kg"] = max(0, current_spec.get("payload_kg", 100) - float(decrease_match.group(1)))

        if "航程" in feedback or "续航" in feedback:
            if increase_match:
                adjustments["range_km"] = current_spec.get("range_km", 200) + float(increase_match.group(1))
            elif decrease_match:
                adjustments["range_km"] = max(0, current_spec.get("range_km", 200) - float(decrease_match.group(1)))

        if "速度" in feedback:
            if increase_match:
                adjustments["cruise_speed_kmh"] = current_spec.get("cruise_speed_kmh", 120) + float(increase_match.group(1))
            elif decrease_match:
                adjustments["cruise_speed_kmh"] = max(0, current_spec.get("cruise_speed_kmh", 120) - float(decrease_match.group(1)))

        return adjustments