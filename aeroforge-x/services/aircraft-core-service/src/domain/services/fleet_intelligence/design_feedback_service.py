"""AeroForge-X v5.0 DesignFeedbackService

Identifies fleet performance trends, creates design feedback tickets,
and tracks tickets through to design update verification.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class TrendDirection(str, Enum):
    OVER_PERFORMANCE = "OverPerformance"
    UNDER_PERFORMANCE = "UnderPerformance"


class TicketStatus(str, Enum):
    OPEN = "Open"
    IN_REVIEW = "InReview"
    DESIGN_UPDATED = "DesignUpdated"
    VERIFIED = "Verified"
    CLOSED = "Closed"


@dataclass(frozen=True)
class PerformanceTrend:
    trend_id: str
    component_type: str
    trend_direction: TrendDirection
    statistical_significance: float
    affected_aircraft_count: int
    operational_data_summary: dict
    potential_design_improvement: str = ""


@dataclass
class DesignFeedbackTicket:
    ticket_id: str
    trend: PerformanceTrend
    status: TicketStatus = TicketStatus.OPEN
    design_update_reference: str = ""
    supporting_data: dict = field(default_factory=dict)
    resolved_at: str = ""

    def to_dict(self) -> dict:
        return {
            "ticket_id": self.ticket_id,
            "trend_id": self.trend.trend_id,
            "component_type": self.trend.component_type,
            "trend_direction": self.trend.trend_direction.value,
            "statistical_significance": self.trend.statistical_significance,
            "affected_aircraft_count": self.trend.affected_aircraft_count,
            "status": self.status.value,
            "design_update_reference": self.design_update_reference,
        }


class DesignFeedbackService:

    def __init__(self, repo=None) -> None:
        self._repo = repo
def __init__(self, repo=None) -> None:
        self._trends: dict[str, PerformanceTrend] = {}
        self._tickets: dict[str, DesignFeedbackTicket] = {}

    def identify_performance_trends(
        self,
        fleet_data: list[dict],
    ) -> list[PerformanceTrend]:
        component_data: dict[str, list[float]] = {}
        for entry in fleet_data:
            ct = entry.get("component_type", "")
            value = entry.get("performance_value", 0.0)
            component_data.setdefault(ct, []).append(value)

        trends: list[PerformanceTrend] = []
        for component_type, values in component_data.items():
            if len(values) < 3:
                continue

            import numpy as np
            arr = np.array(values)
            mean = float(np.mean(arr))
            std = float(np.std(arr))

            if std == 0:
                continue

            design_target = component_data.get(f"{component_type}_target", [mean])[0] if f"{component_type}_target" in component_data else mean

            z_score = (mean - design_target) / std if std > 0 else 0.0
            significance = min(1.0, abs(z_score) / 3.0)

            if significance < 0.5:
                continue

            direction = TrendDirection.OVER_PERFORMANCE if mean > design_target else TrendDirection.UNDER_PERFORMANCE

            improvement = ""
            if direction == TrendDirection.UNDER_PERFORMANCE:
                improvement = f"Consider redesigning {component_type} to improve performance by {abs(mean - design_target):.2f} units"
            else:
                improvement = f"Consider optimizing {component_type} to reduce over-design margin"

            trend = PerformanceTrend(
                trend_id=f"TRD-{uuid.uuid4().hex[:8].upper()}",
                component_type=component_type,
                trend_direction=direction,
                statistical_significance=significance,
                affected_aircraft_count=len(values),
                operational_data_summary={
                    "mean": mean,
                    "std": std,
                    "design_target": design_target,
                    "z_score": z_score,
                },
                potential_design_improvement=improvement,
            )
            self._trends[trend.trend_id] = trend
            trends.append(trend)

        return trends

    def create_design_feedback_ticket(
        self,
        trend: PerformanceTrend,
        supporting_data: dict | None = None,
    ) -> DesignFeedbackTicket:
        ticket = DesignFeedbackTicket(
            ticket_id=f"DFT-{uuid.uuid4().hex[:8].upper()}",
            trend=trend,
            supporting_data=supporting_data or {},
        )
        self._tickets[ticket.ticket_id] = ticket
        return ticket

    def track_feedback_ticket(
        self,
        ticket_id: str,
        new_status: str,
        design_update_reference: str = "",
    ) -> Optional[DesignFeedbackTicket]:
        ticket = self._tickets.get(ticket_id)
        if ticket is None:
            return None

        ticket.status = TicketStatus(new_status)
        if design_update_reference:
            ticket.design_update_reference = design_update_reference

        if new_status in (TicketStatus.VERIFIED.value, TicketStatus.CLOSED.value):
            import time
            ticket.resolved_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        return ticket

    def verify_design_update(
        self,
        ticket_id: str,
        post_update_data: list[dict],
    ) -> Optional[dict]:
        ticket = self._tickets.get(ticket_id)
        if ticket is None:
            return None

        import numpy as np
        values = [d.get("performance_value", 0.0) for d in post_update_data]
        if not values:
            return {"verified": False, "reason": "No post-update data"}

        arr = np.array(values)
        target = ticket.trend.operational_data_summary.get("design_target", float(np.mean(arr)))
        mean = float(np.mean(arr))
        improvement = abs(mean - target) < abs(ticket.trend.operational_data_summary.get("mean", target) - target)

        if improvement:
            ticket.status = TicketStatus.VERIFIED
            return {"verified": True, "improvement": abs(mean - target)}

        return {"verified": False, "reason": "No significant improvement detected"}

    def get_ticket(self, ticket_id: str) -> Optional[DesignFeedbackTicket]:
        return self._tickets.get(ticket_id)