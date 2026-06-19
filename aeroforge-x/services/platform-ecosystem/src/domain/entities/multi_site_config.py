from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from aeroforge_common.domain.base import AggregateRoot


class SyncPolicy(str, Enum):
    REALTIME = "realtime"
    SCHEDULED = "scheduled"
    MANUAL = "manual"


class SiteStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"


@dataclass
class SiteInfo:
    site_id: str
    name: str
    location: str = ""
    timezone: str = "UTC"
    capacity: float = 0.0
    specialization: str = ""
    status: SiteStatus = SiteStatus.ONLINE

    def to_dict(self) -> dict[str, Any]:
        return {
            "site_id": self.site_id,
            "name": self.name,
            "location": self.location,
            "timezone": self.timezone,
            "capacity": self.capacity,
            "specialization": self.specialization,
            "status": self.status.value,
        }


@dataclass
class ConflictResolutionRule:
    rule_id: str
    data_type: str
    resolution_strategy: str = "latest_wins"
    priority_site: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "data_type": self.data_type,
            "resolution_strategy": self.resolution_strategy,
            "priority_site": self.priority_site,
        }


@dataclass
class SyncRecord:
    sync_id: str
    from_site: str
    to_site: str
    data_type: str
    status: str = "completed"
    records_synced: int = 0
    conflicts: int = 0
    synced_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "sync_id": self.sync_id,
            "from_site": self.from_site,
            "to_site": self.to_site,
            "data_type": self.data_type,
            "status": self.status,
            "records_synced": self.records_synced,
            "conflicts": self.conflicts,
            "synced_at": self.synced_at,
        }


class MultiSiteConfig(AggregateRoot):
    def __init__(
        self,
        tenant_id: str,
    ) -> None:
        super().__init__()
        self.tenant_id = tenant_id
        self.sites: list[SiteInfo] = []
        self.sync_policies: list[SyncPolicy] = [SyncPolicy.SCHEDULED]
        self.conflict_resolution_rules: list[ConflictResolutionRule] = []
        self.sync_records: list[SyncRecord] = []
        self.created_at = datetime.now(timezone.utc)

    def add_site(self, site: SiteInfo) -> None:
        self.sites.append(site)

    def remove_site(self, site_id: str) -> bool:
        before = len(self.sites)
        self.sites = [s for s in self.sites if s.site_id != site_id]
        return len(self.sites) < before

    def add_conflict_rule(self, rule: ConflictResolutionRule) -> None:
        self.conflict_resolution_rules.append(rule)

    def add_sync_record(self, record: SyncRecord) -> None:
        self.sync_records.append(record)

    def get_online_sites(self) -> list[SiteInfo]:
        return [s for s in self.sites if s.status == SiteStatus.ONLINE]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "sites_count": len(self.sites),
            "online_sites": len(self.get_online_sites()),
            "sync_records_count": len(self.sync_records),
            "created_at": self.created_at.isoformat(),
        }

    def to_detail_dict(self) -> dict[str, Any]:
        base = self.to_dict()
        base.update({
            "sites": [s.to_dict() for s in self.sites],
            "sync_policies": [p.value for p in self.sync_policies],
            "conflict_resolution_rules": [r.to_dict() for r in self.conflict_resolution_rules],
            "sync_records": [r.to_dict() for r in self.sync_records[-10:]],
        })
        return base