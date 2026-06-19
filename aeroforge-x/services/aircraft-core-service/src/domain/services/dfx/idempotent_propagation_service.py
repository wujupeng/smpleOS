"""AeroForge-X v6.0 IdempotentPropagationService

Ensures exactly-once semantics for configuration change propagation
using idempotency keys, deduplication, and optimistic locking.

INT-2.9: Configuration change propagation idempotency (REQ-DFX-V6-010)
INT-2.10: Real-time dashboard degradation with last-valid-value (REQ-DFX-V6-011)
REQ-NFR-V6-014, REQ-NFR-V6-015
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class PropagationStatus(str, Enum):
    PENDING = "Pending"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    DUPLICATE_SKIPPED = "DuplicateSkipped"
    CONFLICT_REJECTED = "ConflictRejected"
    FAILED = "Failed"


class DashboardDegradationLevel(str, Enum):
    NORMAL = "Normal"
    DEGRADED = "Degraded"
    UNAVAILABLE = "Unavailable"


@dataclass
class IdempotencyRecord:
    idempotency_key: str
    block_id: str
    change_hash: str
    status: PropagationStatus = PropagationStatus.PENDING
    result: dict = field(default_factory=dict)
    processed_at: float = 0.0
    version: int = 0

    def to_dict(self) -> dict:
        return {
            "idempotency_key": self.idempotency_key,
            "block_id": self.block_id,
            "change_hash": self.change_hash,
            "status": self.status.value,
            "result": self.result,
            "processed_at": self.processed_at,
            "version": self.version,
        }


@dataclass
class OptimisticLock:
    resource_id: str
    current_version: int = 0
    locked_by: str = ""
    locked_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "resource_id": self.resource_id,
            "current_version": self.current_version,
            "locked_by": self.locked_by,
            "locked_at": self.locked_at,
        }


@dataclass
class DashboardState:
    dashboard_id: str
    equipment_id: str
    metrics: dict = field(default_factory=dict)
    last_valid_metrics: dict = field(default_factory=dict)
    degradation_level: DashboardDegradationLevel = DashboardDegradationLevel.NORMAL
    last_updated_at: float = 0.0
    is_stale: bool = False
    stale_since: float = 0.0

    def to_dict(self) -> dict:
        return {
            "dashboard_id": self.dashboard_id,
            "equipment_id": self.equipment_id,
            "metrics": self.metrics,
            "last_valid_metrics": self.last_valid_metrics,
            "degradation_level": self.degradation_level.value,
            "last_updated_at": self.last_updated_at,
            "is_stale": self.is_stale,
            "stale_since": self.stale_since,
        }


STALE_THRESHOLD_S = 10.0
DEGRADED_THRESHOLD_S = 30.0
UNAVAILABLE_THRESHOLD_S = 120.0


class IdempotentPropagationService:

    def __init__(self, repo=None) -> None:
        self._repo = repo
def __init__(self, repo=None) -> None:
        self._records: dict[str, IdempotencyRecord] = {}
        self._locks: dict[str, OptimisticLock] = {}
        self._dashboards: dict[str, DashboardState] = {}

    def generateIdempotencyKey(
        self, block_id: str, change_data: dict
    ) -> str:
        data_str = f"{block_id}:{sorted(change_data.items())}"
        return hashlib.sha256(data_str.encode()).hexdigest()[:24]

    def propagateWithIdempotency(
        self,
        block_id: str,
        change_data: dict,
        expected_version: int = 0,
    ) -> IdempotencyRecord:
        key = self.generateIdempotencyKey(block_id, change_data)

        if key in self._records:
            existing = self._records[key]
            if existing.status == PropagationStatus.COMPLETED:
                existing.status = PropagationStatus.DUPLICATE_SKIPPED
                return existing
            if existing.status == PropagationStatus.PROCESSING:
                return existing

        lock = self._locks.get(block_id)
        if lock and lock.current_version != expected_version:
            return IdempotencyRecord(
                idempotency_key=key,
                block_id=block_id,
                change_hash=hashlib.sha256(str(change_data).encode()).hexdigest()[:16],
                status=PropagationStatus.CONFLICT_REJECTED,
                version=expected_version,
            )

        record = IdempotencyRecord(
            idempotency_key=key,
            block_id=block_id,
            change_hash=hashlib.sha256(str(change_data).encode()).hexdigest()[:16],
            status=PropagationStatus.PROCESSING,
            version=expected_version,
        )
        self._records[key] = record

        record.status = PropagationStatus.COMPLETED
        record.processed_at = time.time()
        record.result = {"items_propagated": len(change_data)}

        if block_id in self._locks:
            self._locks[block_id].current_version += 1
        else:
            self._locks[block_id] = OptimisticLock(
                resource_id=block_id, current_version=1
            )

        return record

    def acquireLock(
        self, resource_id: str, locked_by: str
    ) -> OptimisticLock:
        lock = self._locks.get(resource_id, OptimisticLock(resource_id=resource_id))
        lock.locked_by = locked_by
        lock.locked_at = time.time()
        self._locks[resource_id] = lock
        return lock

    def releaseLock(self, resource_id: str) -> None:
        if resource_id in self._locks:
            self._locks[resource_id].locked_by = ""
            self._locks[resource_id].locked_at = 0.0

    def getLock(self, resource_id: str) -> Optional[OptimisticLock]:
        return self._locks.get(resource_id)

    def updateDashboardMetrics(
        self, equipment_id: str, metrics: dict
    ) -> DashboardState:
        dashboard_id = f"DASH-{equipment_id}"
        now = time.time()

        if dashboard_id not in self._dashboards:
            self._dashboards[dashboard_id] = DashboardState(
                dashboard_id=dashboard_id,
                equipment_id=equipment_id,
            )

        dashboard = self._dashboards[dashboard_id]
        dashboard.last_valid_metrics = dict(dashboard.metrics or {})
        dashboard.metrics = metrics
        dashboard.last_updated_at = now
        dashboard.is_stale = False
        dashboard.stale_since = 0.0
        dashboard.degradation_level = DashboardDegradationLevel.NORMAL

        return dashboard

    def checkDashboardDegradation(
        self, equipment_id: str
    ) -> DashboardState:
        dashboard_id = f"DASH-{equipment_id}"
        dashboard = self._dashboards.get(dashboard_id)

        if dashboard is None:
            return DashboardState(
                dashboard_id=dashboard_id,
                equipment_id=equipment_id,
                degradation_level=DashboardDegradationLevel.UNAVAILABLE,
            )

        if dashboard.last_updated_at == 0:
            dashboard.degradation_level = DashboardDegradationLevel.UNAVAILABLE
            return dashboard

        elapsed = time.time() - dashboard.last_updated_at

        if elapsed > UNAVAILABLE_THRESHOLD_S:
            dashboard.degradation_level = DashboardDegradationLevel.UNAVAILABLE
            dashboard.is_stale = True
            dashboard.stale_since = dashboard.last_updated_at + UNAVAILABLE_THRESHOLD_S
        elif elapsed > DEGRADED_THRESHOLD_S:
            dashboard.degradation_level = DashboardDegradationLevel.DEGRADED
            dashboard.is_stale = True
            dashboard.stale_since = dashboard.last_updated_at + DEGRADED_THRESHOLD_S
        elif elapsed > STALE_THRESHOLD_S:
            dashboard.is_stale = True
            dashboard.stale_since = dashboard.last_updated_at + STALE_THRESHOLD_S

        return dashboard

    def getDashboardState(self, equipment_id: str) -> Optional[DashboardState]:
        return self._dashboards.get(f"DASH-{equipment_id}")

    def getRecord(self, idempotency_key: str) -> Optional[IdempotencyRecord]:
        return self._records.get(idempotency_key)