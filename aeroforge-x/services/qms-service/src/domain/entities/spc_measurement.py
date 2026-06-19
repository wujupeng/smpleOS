from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass
class SPCMeasurement:
    id: str = field(default_factory=lambda: str(uuid4()))
    chart_id: str = ""
    sample_group: int = 0
    measurement_values: list[float] = field(default_factory=list)
    mean: float = 0.0
    range_val: float = 0.0
    std_dev: float = 0.0
    is_out_of_control: bool = False
    violation_rules: list[int] = field(default_factory=list)
    measured_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    measured_by: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "chart_id": self.chart_id,
            "sample_group": self.sample_group,
            "measurement_values": self.measurement_values,
            "mean": self.mean,
            "range_val": self.range_val,
            "std_dev": self.std_dev,
            "is_out_of_control": self.is_out_of_control,
            "violation_rules": self.violation_rules,
            "measured_at": self.measured_at,
            "measured_by": self.measured_by,
        }

    def compute_statistics(self) -> None:
        if not self.measurement_values:
            return
        n = len(self.measurement_values)
        self.mean = round(sum(self.measurement_values) / n, 6)
        if n > 1:
            self.range_val = round(max(self.measurement_values) - min(self.measurement_values), 6)
            variance = sum((x - self.mean) ** 2 for x in self.measurement_values) / (n - 1)
            self.std_dev = round(variance ** 0.5, 6)
        else:
            self.range_val = 0.0
            self.std_dev = 0.0