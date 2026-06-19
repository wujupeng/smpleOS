"""AeroForge-X v6.0 StructuredLoggingService

Provides structured logging for v6.0 cross-cutting concerns:
- Configuration change control phase transitions
- Certification evidence package operations
- Supplier quality issue lifecycle transitions

REQ-DFX-V6-002
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class LogEventType(str, Enum):
    CONFIG_CHANGE_PHASE_TRANSITION = "ConfigChangePhaseTransition"
    CERT_EVIDENCE_OPERATION = "CertEvidenceOperation"
    SUPPLIER_ISSUE_LIFECYCLE = "SupplierIssueLifecycle"


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


@dataclass
class StructuredLogEvent:
    log_id: str
    event_type: LogEventType
    level: LogLevel
    message: str
    context: dict = field(default_factory=dict)
    correlation_id: str = ""
    source_service: str = ""
    timestamp: str = ""
    actor: str = ""

    def to_dict(self) -> dict:
        return {
            "log_id": self.log_id,
            "event_type": self.event_type.value,
            "level": self.level.value,
            "message": self.message,
            "context": self.context,
            "correlation_id": self.correlation_id,
            "source_service": self.source_service,
            "timestamp": self.timestamp,
            "actor": self.actor,
        }

    def to_json_line(self) -> str:
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class LogQuery:
    event_type: Optional[LogEventType] = None
    level: Optional[LogLevel] = None
    correlation_id: str = ""
    source_service: str = ""
    actor: str = ""
    limit: int = 100


class StructuredLoggingService:

    def __init__(self, repo=None) -> None:
        self._repo = repo
def __init__(self, repo=None) -> None:
        self._logs: list[StructuredLogEvent] = []

    def logConfigChangeTransition(
        self,
        request_id: str,
        from_phase: str,
        to_phase: str,
        actor: str,
        correlation_id: str = "",
        context: dict | None = None,
    ) -> StructuredLogEvent:
        event = StructuredLogEvent(
            log_id=f"LOG-{uuid.uuid4().hex[:8]}",
            event_type=LogEventType.CONFIG_CHANGE_PHASE_TRANSITION,
            level=LogLevel.INFO,
            message=f"Config change {request_id} transitioned from {from_phase} to {to_phase}",
            context={
                "request_id": request_id,
                "from_phase": from_phase,
                "to_phase": to_phase,
                **(context or {}),
            },
            correlation_id=correlation_id,
            source_service="workflow-engine-service",
            actor=actor,
        )
        self._logs.append(event)
        return event

    def logCertEvidenceOperation(
        self,
        package_id: str,
        operation: str,
        actor: str,
        correlation_id: str = "",
        context: dict | None = None,
    ) -> StructuredLogEvent:
        level = LogLevel.INFO
        if operation in ("lock", "unlock"):
            level = LogLevel.WARN
        elif operation in ("delete", "modify_locked"):
            level = LogLevel.ERROR

        event = StructuredLogEvent(
            log_id=f"LOG-{uuid.uuid4().hex[:8]}",
            event_type=LogEventType.CERT_EVIDENCE_OPERATION,
            level=level,
            message=f"Cert evidence package {package_id} operation: {operation}",
            context={
                "package_id": package_id,
                "operation": operation,
                **(context or {}),
            },
            correlation_id=correlation_id,
            source_service="workflow-engine-service",
            actor=actor,
        )
        self._logs.append(event)
        return event

    def logSupplierIssueLifecycle(
        self,
        issue_id: str,
        from_status: str,
        to_status: str,
        actor: str,
        correlation_id: str = "",
        context: dict | None = None,
    ) -> StructuredLogEvent:
        level = LogLevel.INFO
        if to_status in ("CARIssued", "Reopened"):
            level = LogLevel.WARN
        elif to_status == "Closed":
            level = LogLevel.INFO

        event = StructuredLogEvent(
            log_id=f"LOG-{uuid.uuid4().hex[:8]}",
            event_type=LogEventType.SUPPLIER_ISSUE_LIFECYCLE,
            level=level,
            message=f"Supplier quality issue {issue_id} transitioned from {from_status} to {to_status}",
            context={
                "issue_id": issue_id,
                "from_status": from_status,
                "to_status": to_status,
                **(context or {}),
            },
            correlation_id=correlation_id,
            source_service="workflow-engine-service",
            actor=actor,
        )
        self._logs.append(event)
        return event

    def queryLogs(self, query: LogQuery) -> list[StructuredLogEvent]:
        results = []
        for log in reversed(self._logs):
            if query.event_type and log.event_type != query.event_type:
                continue
            if query.level and log.level != query.level:
                continue
            if query.correlation_id and log.correlation_id != query.correlation_id:
                continue
            if query.source_service and log.source_service != query.source_service:
                continue
            if query.actor and log.actor != query.actor:
                continue
            results.append(log)
            if len(results) >= query.limit:
                break
        return results

    def getLogById(self, log_id: str) -> Optional[StructuredLogEvent]:
        for log in self._logs:
            if log.log_id == log_id:
                return log
        return None

    def getLogsByCorrelationId(self, correlation_id: str) -> list[StructuredLogEvent]:
        return [
            log for log in self._logs if log.correlation_id == correlation_id
        ]