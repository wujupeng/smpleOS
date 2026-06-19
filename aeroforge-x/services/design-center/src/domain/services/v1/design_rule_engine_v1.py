from __future__ import annotations

from typing import Any

from src.domain.entities.v1.design_rule import (
    DesignRule,
    RuleViolation,
    RuleSeverity,
    BUILTIN_DESIGN_RULES,
)


class DesignRuleEngineV1:
    def __init__(self, custom_rules: list[DesignRule] | None = None):
        self._rules: list[DesignRule] = list(BUILTIN_DESIGN_RULES)
        if custom_rules:
            self._rules.extend(custom_rules)

    def validate(self, context: dict[str, Any], domain: str | None = None) -> list[RuleViolation]:
        violations: list[RuleViolation] = []
        for rule in self._rules:
            if domain and rule.domain != domain:
                continue
            violation = rule.evaluate(context)
            if violation:
                violations.append(violation)
        return violations

    def validate_incremental(self, context: dict[str, Any], changed_params: list[str]) -> list[RuleViolation]:
        violations: list[RuleViolation] = []
        for rule in self._rules:
            if not rule.enabled:
                continue
            rule_params = self._extract_rule_parameters(rule)
            if not any(p in changed_params for p in rule_params):
                continue
            violation = rule.evaluate(context)
            if violation:
                violations.append(violation)
        return violations

    def add_rule(self, rule: DesignRule) -> None:
        self._rules.append(rule)

    def disable_rule(self, rule_id: str) -> None:
        for rule in self._rules:
            if rule.rule_id == rule_id:
                rule.enabled = False
                break

    def get_rules(self, domain: str | None = None) -> list[DesignRule]:
        if domain:
            return [r for r in self._rules if r.domain == domain]
        return self._rules

    def _extract_rule_parameters(self, rule: DesignRule) -> list[str]:
        import re
        return list(set(re.findall(r'[a-z_][a-z0-9_]*', rule.condition_expr)))