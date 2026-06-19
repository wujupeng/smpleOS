"""AeroForge-X v6.0 Cross-Program Integration API

RESTful endpoints for cross-Program event-driven integration.
INT-1: 10 integration points across Programs H/I/J/K/E.
"""

from __future__ import annotations

from fastapi import APIRouter

from src.domain.services.integration.cross_program_event_orchestrator_service import (
    CrossProgramEventOrchestratorService,
    IntegrationPoint,
)

router = APIRouter(prefix="/api/v6/workflow-engine/cross-program", tags=["v6-cross-program"])

_service = CrossProgramEventOrchestratorService()


@router.post("/events/route")
async def route_event(body: dict):
    nats_subject = body.get("subject", "")
    payload = body.get("payload", {})
    correlation_id = body.get("correlation_id", "")
    result = _service.routeEvent(nats_subject, payload, correlation_id)
    if result is None:
        return {"routed": False, "reason": "No matching integration point"}
    return {"routed": True, "result": result.to_dict()}


@router.post("/events/mdo-config-update")
async def trigger_mdo_config_update(body: dict):
    result = _service.triggerMDOConfigUpdate(body)
    return result.to_dict()


@router.post("/events/config-twin-update")
async def trigger_config_twin_update(body: dict):
    result = _service.triggerConfigTwinUpdate(body)
    return result.to_dict()


@router.get("/health")
async def get_integration_health():
    health = _service.getIntegrationHealth()
    return [h.to_dict() for h in health]


@router.get("/events")
async def get_event_log(integration_point: str = ""):
    point = None
    if integration_point:
        try:
            point = IntegrationPoint(integration_point)
        except ValueError:
            return {"events": [], "error": "Invalid integration_point"}
    events = _service.getEventLog(point)
    return [e.to_dict() for e in events]


@router.post("/events/{event_id}/retry")
async def retry_failed_event(event_id: str):
    result = _service.retryFailed(event_id)
    if result is None:
        return {"retried": False, "reason": "Event not found"}
    return {"retried": True, "result": result.to_dict()}