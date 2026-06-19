from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from aeroforge_common.domain.base import AggregateRoot, DomainEvent


class TwinType(str, Enum):
    DESIGN = "design"
    MANUFACTURING = "manufacturing"
    FLIGHT = "flight"
    MAINTENANCE = "maintenance"


class SyncStatus(str, Enum):
    REALTIME = "realtime"
    LAGGED = "lagged"
    OFFLINE = "offline"


@dataclass
class SyncLogEntry:
    sync_type: str
    status: str
    records_processed: int = 0
    records_failed: int = 0
    error_details: str | None = None
    synced_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "sync_type": self.sync_type,
            "status": self.status,
            "records_processed": self.records_processed,
            "records_failed": self.records_failed,
            "error_details": self.error_details,
            "synced_at": self.synced_at,
        }


class DigitalTwin(AggregateRoot):
    def __init__(
        self,
        aircraft_serial_number: str,
        twin_type: TwinType = TwinType.DESIGN,
        entity_id: str = "",
        entity_type: str = "",
        twin_id: str | None = None,
    ) -> None:
        super().__init__(twin_id)
        self.aircraft_serial_number: str = aircraft_serial_number
        self.twin_type: TwinType = twin_type
        self.entity_id: str = entity_id
        self.entity_type: str = entity_type
        self.sync_status: SyncStatus = SyncStatus.OFFLINE
        self.last_sync_time: datetime | None = None
        self.data_version: int = 0
        self.twin_payload: dict[str, Any] = {}
        self.sync_logs: list[SyncLogEntry] = []
        self.created_at: datetime = datetime.now(timezone.utc)
        self.updated_at: datetime = datetime.now(timezone.utc)

    def sync(self, sync_type: str, payload: dict[str, Any] | None = None) -> None:
        self.last_sync_time = datetime.now(timezone.utc)
        self.data_version += 1
        if payload:
            self.twin_payload.update(payload)
        self.sync_status = SyncStatus.REALTIME
        self.updated_at = datetime.now(timezone.utc)

        log = SyncLogEntry(
            sync_type=sync_type,
            status="success",
            synced_at=self.last_sync_time.isoformat(),
        )
        self.sync_logs.append(log)
        self.add_domain_event(DomainEvent(
            event_type="twin.synced",
            aggregate_id=self.id,
            payload={
                "twin_id": self.id,
                "aircraft_sn": self.aircraft_serial_number,
                "twin_type": self.twin_type.value,
                "data_version": self.data_version,
            },
        ))

    def check_sync_status(self) -> SyncStatus:
        if self.last_sync_time is None:
            self.sync_status = SyncStatus.OFFLINE
            return self.sync_status

        elapsed = (datetime.now(timezone.utc) - self.last_sync_time).total_seconds()
        if elapsed < 300:
            self.sync_status = SyncStatus.REALTIME
        elif elapsed < 3600:
            self.sync_status = SyncStatus.LAGGED
        else:
            self.sync_status = SyncStatus.OFFLINE

        return self.sync_status

    def detect_data_lag(self) -> dict[str, Any]:
        status = self.check_sync_status()
        lag_seconds = 0.0
        if self.last_sync_time:
            lag_seconds = (datetime.now(timezone.utc) - self.last_sync_time).total_seconds()

        return {
            "twin_id": self.id,
            "aircraft_sn": self.aircraft_serial_number,
            "sync_status": status.value,
            "lag_seconds": round(lag_seconds, 1),
            "is_lagged": status != SyncStatus.REALTIME,
            "last_sync_time": self.last_sync_time.isoformat() if self.last_sync_time else None,
        }

    def restrict_safety_decisions(self) -> dict[str, Any]:
        status = self.check_sync_status()
        restricted = status != SyncStatus.REALTIME
        return {
            "twin_id": self.id,
            "aircraft_sn": self.aircraft_serial_number,
            "safety_decisions_restricted": restricted,
            "reason": f"Twin data is {status.value}" if restricted else None,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "aircraft_serial_number": self.aircraft_serial_number,
            "twin_type": self.twin_type.value,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "sync_status": self.sync_status.value,
            "last_sync_time": self.last_sync_time.isoformat() if self.last_sync_time else None,
            "data_version": self.data_version,
            "twin_payload": self.twin_payload,
            "sync_logs": [l.to_dict() for l in self.sync_logs[-10:]],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }