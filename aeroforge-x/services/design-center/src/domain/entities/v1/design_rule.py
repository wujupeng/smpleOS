from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class RuleType(str, Enum):
    RANGE = "range"
    CONSISTENCY = "consistency"
    COMPLIANCE = "compliance"
    INTERFERENCE = "interference"
    MANUFACTURABILITY = "manufacturability"


class RuleSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class DesignRule:
    rule_id: str = ""
    rule_name: str = ""
    rule_type: RuleType = RuleType.RANGE
    domain: str = ""
    condition_expr: str = ""
    action_expr: str = ""
    priority: int = 50
    severity: RuleSeverity = RuleSeverity.WARNING
    enabled: bool = True
    description: str = ""
    category: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def evaluate(self, context: dict[str, Any]) -> "RuleViolation | None":
        if not self.enabled:
            return None
        try:
            result = eval(self.condition_expr, {"__builtins__": {}}, context)
            if result:
                return None
        except Exception:
            return RuleViolation(
                rule_id=self.rule_id,
                severity=self.severity,
                message=f"Rule '{self.rule_name}' evaluation failed",
                parameter="",
                suggestion=self.action_expr,
            )
        return RuleViolation(
            rule_id=self.rule_id,
            severity=self.severity,
            message=f"Rule '{self.rule_name}' violated: {self.description}",
            parameter="",
            suggestion=self.action_expr,
        )


@dataclass
class RuleViolation:
    rule_id: str
    severity: RuleSeverity
    message: str
    parameter: str
    suggestion: str = ""


BUILTIN_DESIGN_RULES: list[DesignRule] = [
    DesignRule(
        rule_id="AERO-001", rule_name="Aspect Ratio Range", rule_type=RuleType.RANGE,
        domain="airframe", condition_expr="5 <= aspect_ratio <= 25",
        action_expr="Adjust wing span or area", severity=RuleSeverity.ERROR,
        description="Wing aspect ratio must be between 5 and 25", category="aerodynamic",
    ),
    DesignRule(
        rule_id="AERO-002", rule_name="Sweep Angle Range", rule_type=RuleType.RANGE,
        domain="airframe", condition_expr="-5 <= sweep_angle_deg <= 45",
        action_expr="Adjust sweep angle", severity=RuleSeverity.WARNING,
        description="Wing sweep angle must be between -5 and 45 degrees", category="aerodynamic",
    ),
    DesignRule(
        rule_id="AERO-003", rule_name="Taper Ratio Range", rule_type=RuleType.RANGE,
        domain="airframe", condition_expr="0.2 <= taper_ratio <= 1.0",
        action_expr="Adjust root/tip chord ratio", severity=RuleSeverity.WARNING,
        description="Wing taper ratio must be between 0.2 and 1.0", category="aerodynamic",
    ),
    DesignRule(
        rule_id="STR-001", rule_name="Wing Loading Range", rule_type=RuleType.RANGE,
        domain="structure", condition_expr="50 <= wing_loading <= 800",
        action_expr="Adjust wing area or weight", severity=RuleSeverity.ERROR,
        description="Wing loading must be between 50 and 800 kg/m2", category="structural",
    ),
    DesignRule(
        rule_id="STR-002", rule_name="Fuselage Fineness Ratio", rule_type=RuleType.RANGE,
        domain="structure", condition_expr="3 <= fineness_ratio <= 15",
        action_expr="Adjust fuselage length or diameter", severity=RuleSeverity.WARNING,
        description="Fuselage fineness ratio must be between 3 and 15", category="structural",
    ),
    DesignRule(
        rule_id="PWR-001", rule_name="Thrust to Weight Ratio", rule_type=RuleType.RANGE,
        domain="powertrain", condition_expr="thrust_to_weight >= 0.3",
        action_expr="Increase motor power or reduce weight", severity=RuleSeverity.ERROR,
        description="Thrust-to-weight ratio must be at least 0.3", category="propulsion",
    ),
    DesignRule(
        rule_id="PWR-002", rule_name="Battery C-Rating Sufficient", rule_type=RuleType.CONSISTENCY,
        domain="powertrain", condition_expr="max_discharge_c >= required_c_rating",
        action_expr="Select battery with higher C-rating", severity=RuleSeverity.ERROR,
        description="Battery max discharge C-rating must meet required C-rating", category="propulsion",
    ),
    DesignRule(
        rule_id="MFG-001", rule_name="Minimum Wall Thickness", rule_type=RuleType.MANUFACTURABILITY,
        domain="structure", condition_expr="wall_thickness_mm >= 0.5",
        action_expr="Increase wall thickness for manufacturability", severity=RuleSeverity.WARNING,
        description="Minimum wall thickness for manufacturing is 0.5mm", category="manufacturing",
    ),
]