from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from aeroforge_common.domain.base import AggregateRoot, DomainEvent


class AuditAction(str, Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    APPROVE = "approve"
    REJECT = "reject"
    SUBMIT = "submit"
    EXPORT = "export"
    SHARE = "share"
    SYNC = "sync"


class AuditResource(str, Enum):
    TENANT = "tenant"
    PROJECT = "project"
    DESIGN = "design"
    BOM = "bom"
    MES_ORDER = "mes_order"
    QMS_INSPECTION = "qms_inspection"
    CAE_TASK = "cae_task"
    SUPPLIER = "supplier"
    PURCHASE_ORDER = "purchase_order"
    INVENTORY = "inventory"
    SPC_CHART = "spc_chart"
    SCHEDULE = "schedule"
    REPORT = "report"
    USER = "user"
    ROLE = "role"
    PERMISSION = "permission"


@dataclass
class AuditDetail:
    field_name: str
    old_value: Any = None
    new_value: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "field_name": self.field_name,
            "old_value": self.old_value,
            "new_value": self.new_value,
        }


class AuditLog(AggregateRoot):
    def __init__(
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
        task_id: str | None = None,
    ) -> None:
        super().__init__(task_id)
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.action = action
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.resource_name = resource_name
        self.details = details or []
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.request_id = request_id
        self.timestamp = datetime.now(timezone.utc)
        self.signature = ""
        self.chain_previous = ""
        self.chain_hash = ""
        self._compute_signature()

    def _compute_signature(self) -> None:
        payload = json.dumps({
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "action": self.action.value,
            "resource_type": self.resource_type.value,
            "resource_id": self.resource_id,
            "timestamp": self.timestamp.isoformat(),
        }, sort_keys=True)
        self.signature = hashlib.sha256(payload.encode()).hexdigest()

    def verify_integrity(self) -> bool:
        expected = hashlib.sha256(json.dumps({
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "action": self.action.value,
            "resource_type": self.resource_type.value,
            "resource_id": self.resource_id,
            "timestamp": self.timestamp.isoformat(),
        }, sort_keys=True).encode()).hexdigest()
        return self.signature == expected

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "action": self.action.value,
            "resource_type": self.resource_type.value,
            "resource_id": self.resource_id,
            "resource_name": self.resource_name,
            "details": [d.to_dict() for d in self.details],
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat(),
            "signature": self.signature,
            "chain_previous": self.chain_previous,
            "chain_hash": self.chain_hash,
        }