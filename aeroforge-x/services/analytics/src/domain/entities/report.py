from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from aeroforge_common.domain.base import DomainEvent


class ReportFormat(str, Enum):
    PDF = "pdf"
    EXCEL = "excel"
    HTML = "html"


class ReportStatus(str, Enum):
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportTemplate(str, Enum):
    PROJECT_WEEKLY = "project_weekly"
    QUALITY_MONTHLY = "quality_monthly"
    SUPPLIER_QUARTERLY = "supplier_quarterly"
    PRODUCTION_DAILY = "production_daily"
    TRACE_AUDIT = "trace_audit"


@dataclass
class Report:
    id: str = field(default_factory=lambda: str(uuid4()))
    tenant_id: str = ""
    name: str = ""
    report_type: str = ""
    template_id: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    format: ReportFormat = ReportFormat.PDF
    status: ReportStatus = ReportStatus.GENERATING
    file_key: str = ""
    file_size_bytes: int = 0
    schedule_cron: str = ""
    share_token: str = ""
    generated_at: str = ""
    generated_by: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    domain_events: list[DomainEvent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "report_type": self.report_type,
            "template_id": self.template_id,
            "parameters": self.parameters,
            "format": self.format.value,
            "status": self.status.value,
            "file_key": self.file_key,
            "file_size_bytes": self.file_size_bytes,
            "schedule_cron": self.schedule_cron,
            "share_token": self.share_token,
            "generated_at": self.generated_at,
            "generated_by": self.generated_by,
            "created_at": self.created_at,
        }

    def complete(self, file_key: str, file_size: int) -> None:
        self.status = ReportStatus.COMPLETED
        self.file_key = file_key
        self.file_size_bytes = file_size
        self.generated_at = datetime.now(timezone.utc).isoformat()
        self.add_domain_event(DomainEvent(
            event_type="report.completed",
            aggregate_id=self.id,
            payload={"report_id": self.id, "file_key": file_key},
        ))

    def fail(self, error: str = "") -> None:
        self.status = ReportStatus.FAILED

    def add_domain_event(self, event: DomainEvent) -> None:
        self.domain_events.append(event)