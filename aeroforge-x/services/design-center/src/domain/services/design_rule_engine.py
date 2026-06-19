from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Violation:
    rule_id: str
    severity: str
    message: str
    suggestion: str
    parameter: str = ""


class AerodynamicRuleSet:
    RULES: list[dict[str, Any]] = [
        {"id": "AERO-001", "param": "aspect_ratio", "min": 5, "max": 25, "severity": "error",
         "message": "展弦比超出合理范围", "suggestion": "固定翼展弦比建议在5-25之间"},
        {"id": "AERO-002", "param": "wing_sweep_deg", "min": -5, "max": 45, "severity": "warning",
         "message": "后掠角超出常规范围", "suggestion": "低速飞机后掠角通常在0-10度"},
        {"id": "AERO-003", "param": "taper_ratio", "min": 0.2, "max": 1.0, "severity": "error",
         "message": "根梢比超出合理范围", "suggestion": "根梢比建议在0.2-1.0之间"},
    ]

    def check(self, params: dict[str, Any]) -> list[Violation]:
        violations: list[Violation] = []
        for rule in self.RULES:
            value = params.get(rule["param"])
            if value is not None:
                if isinstance(value, (int, float)):
                    if value < rule["min"] or value > rule["max"]:
                        violations.append(Violation(
                            rule_id=rule["id"],
                            severity=rule["severity"],
                            message=rule["message"],
                            suggestion=rule["suggestion"],
                            parameter=rule["param"],
                        ))
        return violations


class StructuralRuleSet:
    RULES: list[dict[str, Any]] = [
        {"id": "STR-001", "param": "wing_loading", "min": 50, "max": 800, "severity": "error",
         "message": "翼载超出合理范围", "suggestion": "轻型飞机翼载建议在50-300 N/m²"},
        {"id": "STR-002", "param": "fineness_ratio", "min": 3, "max": 15, "severity": "warning",
         "message": "长细比超出常规范围", "suggestion": "机身长细比建议在5-10之间"},
    ]

    def check(self, params: dict[str, Any]) -> list[Violation]:
        violations: list[Violation] = []
        for rule in self.RULES:
            value = params.get(rule["param"])
            if value is not None:
                if isinstance(value, (int, float)):
                    if value < rule["min"] or value > rule["max"]:
                        violations.append(Violation(
                            rule_id=rule["id"],
                            severity=rule["severity"],
                            message=rule["message"],
                            suggestion=rule["suggestion"],
                            parameter=rule["param"],
                        ))
        return violations


class RuleExecutor:
    def __init__(self) -> None:
        self._rule_sets = [AerodynamicRuleSet(), StructuralRuleSet()]

    def validate(self, model_params: dict[str, Any]) -> list[Violation]:
        all_violations: list[Violation] = []
        for rule_set in self._rule_sets:
            all_violations.extend(rule_set.check(model_params))
        return all_violations

    def validate_incremental(self, model_params: dict[str, Any], changed_params: list[str]) -> list[Violation]:
        all_violations = self.validate(model_params)
        return [v for v in all_violations if v.parameter in changed_params]


class DesignRuleEngine:
    def __init__(self) -> None:
        self._executor = RuleExecutor()

    def validate(self, model_params: dict[str, Any]) -> list[dict[str, Any]]:
        violations = self._executor.validate(model_params)
        return [
            {
                "rule_id": v.rule_id,
                "severity": v.severity,
                "message": v.message,
                "suggestion": v.suggestion,
                "parameter": v.parameter,
            }
            for v in violations
        ]

    def validate_incremental(self, model_params: dict[str, Any], changed_params: list[str]) -> list[dict[str, Any]]:
        violations = self._executor.validate_incremental(model_params, changed_params)
        return [
            {
                "rule_id": v.rule_id,
                "severity": v.severity,
                "message": v.message,
                "suggestion": v.suggestion,
                "parameter": v.parameter,
            }
            for v in violations
        ]