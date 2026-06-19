"""AeroForge-X v6.0 DFX API (workflow-engine-service)

Endpoints for structured logging, audit trail, and cross-program integration.
"""

from __future__ import annotations

from fastapi import APIRouter

from src.domain.services.dfx.structured_logging_service import (
    StructuredLoggingService,
    LogEventType,
    LogLevel,
    LogQuery,
)
from src.domain.services.dfx.audit_trail_service import (
    AuditTrailService,
    AuditAction,
    AuditSeverity,
    AuditQuery,
)
from src.domain.services.integration.cross_program_event_orchestrator_service import (
    CrossProgramEventOrchestratorService,
    IntegrationPoint,
)

router = APIRouter(prefix="/api/v6/workflow-engine/dfx", tags=["v6-dfx"])

_logging_svc = StructuredLoggingService()
_audit_svc = AuditTrailService()
_orchestrator_svc = CrossProgramEventOrchestratorService()


@router.post("/logging/config-change")
async def log_config_change_transition(body: dict):
    event = _logging_svc.logConfigChangeTransition(
        request_id=body.get("request_id", ""),
        from_phase=body.get("from_phase", ""),
        to_phase=body.get("to_phase", ""),
        actor=body.get("actor", ""),
        correlation_id=body.get("correlation_id", ""),
        context=body.get("context"),
    )
    return event.to_dict()


@router.post("/logging/cert-evidence")
async def log_cert_evidence_operation(body: dict):
    event = _logging_svc.logCertEvidenceOperation(
        package_id=body.get("package_id", ""),
        operation=body.get("operation", ""),
        actor=body.get("actor", ""),
        correlation_id=body.get("correlation_id", ""),
        context=body.get("context"),
    )
    return event.to_dict()


@router.post("/logging/supplier-issue")
async def log_supplier_issue_lifecycle(body: dict):
    event = _logging_svc.logSupplierIssueLifecycle(
        issue_id=body.get("issue_id", ""),
        from_status=body.get("from_status", ""),
        to_status=body.get("to_status", ""),
        actor=body.get("actor", ""),
        correlation_id=body.get("correlation_id", ""),
        context=body.get("context"),
    )
    return event.to_dict()


@router.get("/logging/query")
async def query_logs(
    event_type: str = "",
    level: str = "",
    correlation_id: str = "",
    limit: int = 100,
):
    query = LogQuery(
        event_type=LogEventType(event_type) if event_type else None,
        level=LogLevel(level) if level else None,
        correlation_id=correlation_id,
        limit=limit,
    )
    logs = _logging_svc.queryLogs(query)
    return [l.to_dict() for l in logs]


@router.post("/audit/record")
async def record_audit_entry(body: dict):
    entry = _audit_svc.recordAudit(
        action=AuditAction(body.get("action", "")),
        resource_type=body.get("resource_type", ""),
        resource_id=body.get("resource_id", ""),
        actor=body.get("actor", ""),
        actor_role=body.get("actor_role", ""),
        details=body.get("details"),
        previous_state_hash=body.get("previous_state_hash", ""),
        new_state_hash=body.get("new_state_hash", ""),
        correlation_id=body.get("correlation_id", ""),
        source_ip=body.get("source_ip", ""),
        timestamp=body.get("timestamp", ""),
    )
    return entry.to_dict()


@router.get("/audit/verify")
async def verify_audit_integrity():
    return _audit_svc.verifyIntegrity()


@router.get("/audit/query")
async def query_audit_trail(
    action: str = "",
    resource_type: str = "",
    resource_id: str = "",
    actor: str = "",
    severity: str = "",
    correlation_id: str = "",
    limit: int = 100,
):
    query = AuditQuery(
        action=AuditAction(action) if action else None,
        resource_type=resource_type,
        resource_id=resource_id,
        actor=actor,
        severity=AuditSeverity(severity) if severity else None,
        correlation_id=correlation_id,
        limit=limit,
    )
    entries = _audit_svc.queryAuditTrail(query)
    return [e.to_dict() for e in entries]


@router.post("/integration/route")
async def route_cross_program_event(body: dict):
    nats_subject = body.get("subject", "")
    payload = body.get("payload", {})
    correlation_id = body.get("correlation_id", "")
    result = _orchestrator_svc.routeEvent(nats_subject, payload, correlation_id)
    if result is None:
        return {"routed": False, "reason": "No matching integration point"}
    return {"routed": True, "result": result.to_dict()}


@router.get("/integration/health")
async def get_integration_health():
    health = _orchestrator_svc.getIntegrationHealth()
    return [h.to_dict() for h in health]


@router.get("/integration/events")
async def get_integration_events(integration_point: str = ""):
    point = None
    if integration_point:
        try:
            point = IntegrationPoint(integration_point)
        except ValueError:
            return {"events": [], "error": "Invalid integration_point"}
    events = _orchestrator_svc.getEventLog(point)
    return [e.to_dict() for e in events]