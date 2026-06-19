from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from aeroforge_common.domain.base import DomainEvent


class ChartType(str, Enum):
    X_BAR_R = "x_bar_r"
    X_BAR_S = "x_bar_s"
    P = "p"
    C = "c"
    U = "u"
    EWMA = "ewma"
    CUSUM = "cusum"


class ChartStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


@dataclass
class SpecificationLimits:
    usl: float = 0.0
    lsl: float = 0.0
    target: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {"usl": self.usl, "lsl": self.lsl, "target": self.target}


@dataclass
class ControlLimits:
    ucl: float = 0.0
    lcl: float = 0.0
    cl: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {"ucl": self.ucl, "lcl": self.lcl, "cl": self.cl}


@dataclass
class OutOfControlRule:
    rule_id: int
    name: str
    description: str
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
        }


DEFAULT_OOC_RULES: list[OutOfControlRule] = [
    OutOfControlRule(1, "单点超3σ", "单点超出3σ控制限"),
    OutOfControlRule(2, "9点同侧", "连续9点在中心线同一侧"),
    OutOfControlRule(3, "6点趋势", "连续6点递增或递减"),
    OutOfControlRule(4, "14点交替", "连续14点交替上下"),
    OutOfControlRule(5, "3点2超2σ", "连续3点中2点超出2σ"),
    OutOfControlRule(6, "5点4超1σ", "连续5点中4点超出1σ"),
    OutOfControlRule(7, "15点在1σ内", "连续15点在1σ内"),
    OutOfControlRule(8, "8点超1σ", "连续8点超出1σ且在3σ内"),
]


@dataclass
class SPCControlChart:
    id: str = field(default_factory=lambda: str(uuid4()))
    tenant_id: str = ""
    project_id: str = ""
    chart_type: ChartType = ChartType.X_BAR_R
    process_name: str = ""
    characteristic_name: str = ""
    specification_limits: SpecificationLimits = field(default_factory=SpecificationLimits)
    control_limits: ControlLimits = field(default_factory=ControlLimits)
    sample_size: int = 5
    sampling_frequency: str = "per_lot"
    status: ChartStatus = ChartStatus.ACTIVE
    out_of_control_rules: list[OutOfControlRule] = field(default_factory=lambda: DEFAULT_OOC_RULES.copy())
    created_by: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    domain_events: list[DomainEvent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "chart_type": self.chart_type.value,
            "process_name": self.process_name,
            "characteristic_name": self.characteristic_name,
            "specification_limits": self.specification_limits.to_dict(),
            "control_limits": self.control_limits.to_dict(),
            "sample_size": self.sample_size,
            "sampling_frequency": self.sampling_frequency,
            "status": self.status.value,
            "out_of_control_rules": [r.to_dict() for r in self.out_of_control_rules],
            "created_by": self.created_by,
            "created_at": self.created_at,
        }

    def set_control_limits(self, ucl: float, lcl: float, cl: float) -> None:
        self.control_limits = ControlLimits(ucl=ucl, lcl=lcl, cl=cl)

    def suspend(self) -> None:
        self.status = ChartStatus.SUSPENDED

    def activate(self) -> None:
        self.status = ChartStatus.ACTIVE

    def add_domain_event(self, event: DomainEvent) -> None:
        self.domain_events.append(event)