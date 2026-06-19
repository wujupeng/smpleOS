from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime, timezone
from typing import Any

from aeroforge_common.domain.base import DomainEvent

from ..entities.audit_log import AuditAction, AuditDetail, AuditLog, AuditResource

logger = logging.getLogger(__name__)


class AuditQueryFilter:
    def __init__(
        self,
        tenant_id: str | None = None,
        user_id: str | None = None,
        action: AuditAction | None = None,
        resource_type: AuditResource | None = None,
        resource_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        request_id: str | None = None,
        ip_address: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> None:
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.action = action
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.start_time = start_time
        self.end_time = end_time
        self.request_id = request_id
        self.ip_address = ip_address
        self.page = max(1, page)
        self.page_size = min(100, max(1, page_size))


class AuditDomainService:
    def __init__(self) -> None:
        self._logs: list[AuditLog] = []
        self._id_index: dict[str, AuditLog] = {}
        self._chain_hash: str = "0" * 64

    def record(
        self,
        tenant_id: str,
        user_id: str,
        action: AuditAction,
        resource_type: AuditResource,
        resource_id: str,
        resource_name: str = "",
        details: list[AuditDetail] | None = None,
        ip_address: str = "",
        user_agent: str = "",
        request_id: str = "",
    ) -> AuditLog:
        log = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )
        log.chain_previous = self._chain_hash
        self._chain_hash = self._compute_chain_hash(log)
        log.chain_hash = self._chain_hash

        self._logs.append(log)
        self._id_index[log.id] = log

        log.add_domain_event(DomainEvent(
            event_type="audit.recorded",
            aggregate_id=log.id,
            payload={
                "tenant_id": tenant_id,
                "user_id": user_id,
                "action": action.value,
                "resource_type": resource_type.value,
                "resource_id": resource_id,
            },
        ))

        logger.info(
            "Audit: tenant=%s user=%s action=%s resource=%s/%s",
            tenant_id, user_id, action.value, resource_type.value, resource_id,
        )
        return log

    def get_log(self, log_id: str) -> AuditLog | None:
        return self._id_index.get(log_id)

    def query(self, filter_params: AuditQueryFilter) -> dict[str, Any]:
        results = list(self._logs)

        if filter_params.tenant_id:
            results = [l for l in results if l.tenant_id == filter_params.tenant_id]
        if filter_params.user_id:
            results = [l for l in results if l.user_id == filter_params.user_id]
        if filter_params.action:
            results = [l for l in results if l.action == filter_params.action]
        if filter_params.resource_type:
            results = [l for l in results if l.resource_type == filter_params.resource_type]
        if filter_params.resource_id:
            results = [l for l in results if l.resource_id == filter_params.resource_id]
        if filter_params.start_time:
            results = [l for l in results if l.timestamp >= filter_params.start_time]
        if filter_params.end_time:
            results = [l for l in results if l.timestamp <= filter_params.end_time]
        if filter_params.request_id:
            results = [l for l in results if l.request_id == filter_params.request_id]
        if filter_params.ip_address:
            results = [l for l in results if l.ip_address == filter_params.ip_address]

        results.sort(key=lambda l: l.timestamp, reverse=True)

        total = len(results)
        start = (filter_params.page - 1) * filter_params.page_size
        end = start + filter_params.page_size
        page_results = results[start:end]

        return {
            "total": total,
            "page": filter_params.page,
            "page_size": filter_params.page_size,
            "logs": [l.to_dict() for l in page_results],
        }

    def verify_chain_integrity(self, tenant_id: str | None = None) -> dict[str, Any]:
        logs = self._logs
        if tenant_id:
            logs = [l for l in logs if l.tenant_id == tenant_id]

        tampered_ids: list[str] = []
        chain_breaks: list[str] = []

        for log in logs:
            if not log.verify_integrity():
                tampered_ids.append(log.id)

        sorted_logs = sorted(logs, key=lambda l: l.timestamp)
        for i in range(1, len(sorted_logs)):
            prev = sorted_logs[i - 1]
            curr = sorted_logs[i]
            if hasattr(curr, "chain_previous") and curr.chain_previous != prev.chain_hash:
                chain_breaks.append(curr.id)

        return {
            "verified": len(tampered_ids) == 0 and len(chain_breaks) == 0,
            "total_logs": len(logs),
            "tampered_count": len(tampered_ids),
            "chain_break_count": len(chain_breaks),
            "tampered_ids": tampered_ids,
            "chain_break_ids": chain_breaks,
        }

    def export_csv(self, filter_params: AuditQueryFilter) -> str:
        result = self.query(filter_params)
        logs = result["logs"]

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id", "tenant_id", "user_id", "action", "resource_type",
            "resource_id", "resource_name", "ip_address", "user_agent",
            "request_id", "timestamp", "signature", "details",
        ])

        for log in logs:
            details_str = json.dumps(log.get("details", []), ensure_ascii=False)
            writer.writerow([
                log.get("id", ""),
                log.get("tenant_id", ""),
                log.get("user_id", ""),
                log.get("action", ""),
                log.get("resource_type", ""),
                log.get("resource_id", ""),
                log.get("resource_name", ""),
                log.get("ip_address", ""),
                log.get("user_agent", ""),
                log.get("request_id", ""),
                log.get("timestamp", ""),
                log.get("signature", ""),
                details_str,
            ])

        return output.getvalue()

    def export_json(self, filter_params: AuditQueryFilter) -> str:
        result = self.query(filter_params)
        return json.dumps(result, ensure_ascii=False, indent=2, default=str)

    def get_statistics(self, tenant_id: str) -> dict[str, Any]:
        logs = [l for l in self._logs if l.tenant_id == tenant_id]

        action_counts: dict[str, int] = {}
        resource_counts: dict[str, int] = {}
        user_counts: dict[str, int] = {}

        for log in logs:
            action_counts[log.action.value] = action_counts.get(log.action.value, 0) + 1
            resource_counts[log.resource_type.value] = resource_counts.get(log.resource_type.value, 0) + 1
            user_counts[log.user_id] = user_counts.get(log.user_id, 0) + 1

        return {
            "tenant_id": tenant_id,
            "total_logs": len(logs),
            "action_counts": action_counts,
            "resource_counts": resource_counts,
            "top_users": sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            "first_log": min((l.timestamp for l in logs), default=None),
            "last_log": max((l.timestamp for l in logs), default=None),
        }

    def _compute_chain_hash(self, log: AuditLog) -> str:
        import hashlib
        payload = json.dumps({
            "previous_hash": self._chain_hash,
            "log_id": log.id,
            "tenant_id": log.tenant_id,
            "user_id": log.user_id,
            "action": log.action.value,
            "resource_type": log.resource_type.value,
            "resource_id": log.resource_id,
            "timestamp": log.timestamp.isoformat(),
        }, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()