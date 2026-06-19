"""AeroForge-X v6.0 AuditTrailService

Immutable audit trail for v6.0 critical operations:
- Configuration baseline changes
- Certification evidence modifications
- Supplier quality operations
- Shop floor control commands

REQ-DFX-V6-007, REQ-NFR-V6-023
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class AuditAction(str, Enum):
    BASELINE_ESTABLISH = "BaselineEstablish"
    BASELINE_FREEZE = "BaselineFreeze"
    BASELINE_MODIFY = "BaselineModify"
    BASELINE_DELETE = "BaselineDelete"
    EVIDENCE_ADD = "EvidenceAdd"
    EVIDENCE_MODIFY = "EvidenceModify"
    EVIDENCE_LOCK = "EvidenceLock"
    EVIDENCE_DELETE = "EvidenceDelete"
    SUPPLIER_QUALITY_CREATE = "SupplierQualityCreate"
    SUPPLIER_QUALITY_UPDATE = "SupplierQualityUpdate"
    SUPPLIER_CAR_ISSUE = "SupplierCARIssue"
    SUPPLIER_CAR_VERIFY = "SupplierCARVerify"
    SHOP_FLOOR_COMMAND_ISSUE = "ShopFloorCommandIssue"
    SHOP_FLOOR_COMMAND_EXECUTE = "ShopFloorCommandExecute"
    SHOP_FLOOR_COMMAND_REJECT = "ShopFloorCommandReject"


class AuditSeverity(str, Enum):
    INFORMATIONAL = "Informational"
    WARNING = "Warning"
    CRITICAL = "Critical"


@dataclass
class AuditEntry:
    audit_id: str
    action: AuditAction
    resource_type: str
    resource_id: str
    actor: str
    actor_role: str
    details: dict = field(default_factory=dict)
    previous_state_hash: str = ""
    new_state_hash: str = ""
    severity: AuditSeverity = AuditSeverity.INFORMATIONAL
    timestamp: str = ""
    source_ip: str = ""
    correlation_id: str = ""
    immutable_hash: str = ""

    def to_dict(self) -> dict:
        return {
            "audit_id": self.audit_id,
            "action": self.action.value,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "actor": self.actor,
            "actor_role": self.actor_role,
            "details": self.details,
            "previous_state_hash": self.previous_state_hash,
            "new_state_hash": self.new_state_hash,
            "severity": self.severity.value,
            "timestamp": self.timestamp,
            "source_ip": self.source_ip,
            "correlation_id": self.correlation_id,
            "immutable_hash": self.immutable_hash,
        }


@dataclass
class AuditQuery:
    action: Optional[AuditAction] = None
    resource_type: str = ""
    resource_id: str = ""
    actor: str = ""
    severity: Optional[AuditSeverity] = None
    correlation_id: str = ""
    limit: int = 100


ACTION_SEVERITY_MAP = {
    AuditAction.BASELINE_ESTABLISH: AuditSeverity.INFORMATIONAL,
    AuditAction.BASELINE_FREEZE: AuditSeverity.WARNING,
    AuditAction.BASELINE_MODIFY: AuditSeverity.CRITICAL,
    AuditAction.BASELINE_DELETE: AuditSeverity.CRITICAL,
    AuditAction.EVIDENCE_ADD: AuditSeverity.INFORMATIONAL,
    AuditAction.EVIDENCE_MODIFY: AuditSeverity.WARNING,
    AuditAction.EVIDENCE_LOCK: AuditSeverity.WARNING,
    AuditAction.EVIDENCE_DELETE: AuditSeverity.CRITICAL,
    AuditAction.SUPPLIER_QUALITY_CREATE: AuditSeverity.INFORMATIONAL,
    AuditAction.SUPPLIER_QUALITY_UPDATE: AuditSeverity.INFORMATIONAL,
    AuditAction.SUPPLIER_CAR_ISSUE: AuditSeverity.WARNING,
    AuditAction.SUPPLIER_CAR_VERIFY: AuditSeverity.INFORMATIONAL,
    AuditAction.SHOP_FLOOR_COMMAND_ISSUE: AuditSeverity.WARNING,
    AuditAction.SHOP_FLOOR_COMMAND_EXECUTE: AuditSeverity.CRITICAL,
    AuditAction.SHOP_FLOOR_COMMAND_REJECT: AuditSeverity.WARNING,
}


class AuditTrailService:

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []
        self._hash_chain: list[str] = []

    def recordAudit(
        self,
        action: AuditAction,
        resource_type: str,
        resource_id: str,
        actor: str,
        actor_role: str,
        details: dict | None = None,
        previous_state_hash: str = "",
        new_state_hash: str = "",
        correlation_id: str = "",
        source_ip: str = "",
        timestamp: str = "",
    ) -> AuditEntry:
        severity = ACTION_SEVERITY_MAP.get(action, AuditSeverity.INFORMATIONAL)

        entry = AuditEntry(
            audit_id=f"AUD-{uuid.uuid4().hex[:8]}",
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            actor=actor,
            actor_role=actor_role,
            details=details or {},
            previous_state_hash=previous_state_hash,
            new_state_hash=new_state_hash,
            severity=severity,
            timestamp=timestamp,
            source_ip=source_ip,
            correlation_id=correlation_id,
        )

        entry.immutable_hash = self._compute_immutable_hash(entry)
        self._entries.append(entry)
        self._hash_chain.append(entry.immutable_hash)

        return entry

    def _compute_immutable_hash(self, entry: AuditEntry) -> str:
        prev_hash = self._hash_chain[-1] if self._hash_chain else "genesis"
        data = (
            f"{entry.audit_id}|{entry.action.value}|{entry.resource_type}|"
            f"{entry.resource_id}|{entry.actor}|{entry.timestamp}|{prev_hash}"
        )
        return hashlib.sha256(data.encode()).hexdigest()

    def verifyIntegrity(self) -> dict:
        if not self._entries:
            return {"valid": True, "entries_checked": 0}

        for i, entry in enumerate(self._entries):
            prev_hash = self._hash_chain[i - 1] if i > 0 else "genesis"
            data = (
                f"{entry.audit_id}|{entry.action.value}|{entry.resource_type}|"
                f"{entry.resource_id}|{entry.actor}|{entry.timestamp}|{prev_hash}"
            )
            expected = hashlib.sha256(data.encode()).hexdigest()
            if entry.immutable_hash != expected:
                return {
                    "valid": False,
                    "entries_checked": i + 1,
                    "tampered_entry": entry.audit_id,
                }

        return {"valid": True, "entries_checked": len(self._entries)}

    def queryAuditTrail(self, query: AuditQuery) -> list[AuditEntry]:
        results = []
        for entry in reversed(self._entries):
            if query.action and entry.action != query.action:
                continue
            if query.resource_type and entry.resource_type != query.resource_type:
                continue
            if query.resource_id and entry.resource_id != query.resource_id:
                continue
            if query.actor and entry.actor != query.actor:
                continue
            if query.severity and entry.severity != query.severity:
                continue
            if query.correlation_id and entry.correlation_id != query.correlation_id:
                continue
            results.append(entry)
            if len(results) >= query.limit:
                break
        return results

    def getAuditById(self, audit_id: str) -> Optional[AuditEntry]:
        for entry in self._entries:
            if entry.audit_id == audit_id:
                return entry
        return None

    def getCorrelationChain(self, correlation_id: str) -> list[AuditEntry]:
        return [
            e for e in self._entries if e.correlation_id == correlation_id
        ]