from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from src.domain.value_objects.enums import TraceType, TraceSourceType


@dataclass
class RequirementTrace:
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_type: TraceSourceType = TraceSourceType.SPEC
    source_id: str = ""
    target_type: TraceSourceType = TraceSourceType.DESIGN_OBJECT
    target_id: str = ""
    trace_type: TraceType = TraceType.SATISFIES
    confidence: Decimal = Decimal("1.00")
    created_by: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def validate(self) -> list[str]:
        violations = []
        if not self.source_id:
            violations.append("source_id is required")
        if not self.target_id:
            violations.append("target_id is required")
        if self.source_id == self.target_id and self.source_type == self.target_type:
            violations.append("Self-referencing trace is not allowed")
        if self.confidence < Decimal("0") or self.confidence > Decimal("1"):
            violations.append(f"Confidence {self.confidence} must be between 0 and 1")
        return violations