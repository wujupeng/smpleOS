from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.services.fleet_intelligence.design_feedback_service import (
    DesignFeedbackService,
    PerformanceTrend,
    TrendDirection,
)

router = APIRouter(prefix="/api/v5/aircraft-core/design-feedback", tags=["Design Feedback v5"])

_service = DesignFeedbackService()


@router.post("/trends")
async def identify_performance_trends(body: dict[str, Any]):
    fleet_data = body.get("fleet_data", [])
    trends = _service.identify_performance_trends(fleet_data=fleet_data)
    return {
        "trends": [
            {
                "trend_id": t.trend_id,
                "component_type": t.component_type,
                "trend_direction": t.trend_direction.value,
                "statistical_significance": t.statistical_significance,
                "affected_aircraft_count": t.affected_aircraft_count,
                "operational_data_summary": t.operational_data_summary,
                "potential_design_improvement": t.potential_design_improvement,
            }
            for t in trends
        ],
    }


@router.post("/tickets")
async def create_feedback_ticket(body: dict[str, Any]):
    trend_data = body.get("trend", {})
    trend = PerformanceTrend(
        trend_id=trend_data.get("trend_id", ""),
        component_type=trend_data.get("component_type", ""),
        trend_direction=TrendDirection(trend_data.get("trend_direction", "UnderPerformance")),
        statistical_significance=trend_data.get("statistical_significance", 0.5),
        affected_aircraft_count=trend_data.get("affected_aircraft_count", 0),
        operational_data_summary=trend_data.get("operational_data_summary", {}),
        potential_design_improvement=trend_data.get("potential_design_improvement", ""),
    )
    ticket = _service.create_design_feedback_ticket(
        trend=trend,
        supporting_data=body.get("supporting_data"),
    )
    return ticket.to_dict()


@router.get("/tickets/{ticket_id}")
async def get_feedback_ticket(ticket_id: str):
    ticket = _service.get_ticket(ticket_id=ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket.to_dict()


@router.post("/tickets/{ticket_id}/verify")
async def verify_design_update(ticket_id: str, body: dict[str, Any]):
    post_update_data = body.get("post_update_data", [])
    result = _service.verify_design_update(
        ticket_id=ticket_id,
        post_update_data=post_update_data,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return result