from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class VerificationResult(str, Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    NEEDS_REVIEW = "needs_review"


class VerificationType(str, Enum):
    DESIGN = "design"
    MANUFACTURING = "manufacturing"
    TEST = "test"


@dataclass
class VerificationCheck:
    check_id: str
    regulation_clause: str
    check_description: str
    expected_value: str
    actual_value: str
    result: VerificationResult = VerificationResult.NEEDS_REVIEW
    deviation: float = 0.0
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "regulation_clause": self.regulation_clause,
            "check_description": self.check_description,
            "expected_value": self.expected_value,
            "actual_value": self.actual_value,
            "result": self.result.value,
            "deviation": round(self.deviation, 4),
            "notes": self.notes,
        }


@dataclass
class VerificationReport:
    report_id: str
    plan_id: str
    verification_type: VerificationType
    checks: list[VerificationCheck] = field(default_factory=list)
    overall_result: VerificationResult = VerificationResult.NEEDS_REVIEW
    compliant_count: int = 0
    non_compliant_count: int = 0
    needs_review_count: int = 0
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "plan_id": self.plan_id,
            "verification_type": self.verification_type.value,
            "overall_result": self.overall_result.value,
            "compliant_count": self.compliant_count,
            "non_compliant_count": self.non_compliant_count,
            "needs_review_count": self.needs_review_count,
            "checks": [c.to_dict() for c in self.checks],
            "generated_at": self.generated_at.isoformat(),
        }