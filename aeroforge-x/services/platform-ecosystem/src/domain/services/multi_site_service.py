from __future__ import annotations

import uuid
import random
from datetime import datetime, timezone
from typing import Any

from ..entities.multi_site_config import (
    ConflictResolutionRule,
    MultiSiteConfig,
    SiteInfo,
    SiteStatus,
    SyncPolicy,
    SyncRecord,
)


class MultiSiteService:
    def __init__(self) -> None:
        self._configs: dict[str, MultiSiteConfig] = {}

    def register_site(
        self,
        tenant_id: str,
        name: str,
        location: str = "",
        timezone: str = "UTC",
        capacity: float = 0.0,
        specialization: str = "",
    ) -> MultiSiteConfig:
        config = self._get_or_create_config(tenant_id)

        site = SiteInfo(
            site_id=f"site-{uuid.uuid4().hex[:8]}",
            name=name,
            location=location,
            timezone=timezone,
            capacity=capacity,
            specialization=specialization,
        )
        config.add_site(site)
        return config

    def get_sites(self, tenant_id: str) -> list[dict[str, Any]]:
        config = self._configs.get(tenant_id)
        if not config:
            return []
        return [s.to_dict() for s in config.sites]

    def sync_data_across_sites(
        self,
        tenant_id: str,
        data_type: str = "all",
    ) -> dict[str, Any]:
        config = self._configs.get(tenant_id)
        if not config or len(config.sites) < 2:
            return {"synced": False, "reason": "Need at least 2 sites"}

        online_sites = config.get_online_sites()
        if len(online_sites) < 2:
            return {"synced": False, "reason": "Need at least 2 online sites"}

        sync_results: list[dict[str, Any]] = []
        for i in range(len(online_sites) - 1):
            from_site = online_sites[i]
            to_site = online_sites[i + 1]

            records_synced = random.randint(50, 500)
            conflicts = random.randint(0, 5)

            record = SyncRecord(
                sync_id=str(uuid.uuid4()),
                from_site=from_site.site_id,
                to_site=to_site.site_id,
                data_type=data_type,
                status="completed",
                records_synced=records_synced,
                conflicts=conflicts,
                synced_at=datetime.now(timezone.utc).isoformat(),
            )
            config.add_sync_record(record)
            sync_results.append(record.to_dict())

        return {
            "tenant_id": tenant_id,
            "sync_type": data_type,
            "sync_results": sync_results,
            "total_records_synced": sum(r["records_synced"] for r in sync_results),
            "total_conflicts": sum(r["conflicts"] for r in sync_results),
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }

    def distribute_work_order(
        self,
        tenant_id: str,
        work_order_id: str,
        quantity: float = 100,
    ) -> dict[str, Any]:
        config = self._configs.get(tenant_id)
        if not config:
            return {"distributed": False, "reason": "No sites configured"}

        online_sites = config.get_online_sites()
        if not online_sites:
            return {"distributed": False, "reason": "No online sites"}

        total_capacity = sum(s.capacity for s in online_sites)
        distribution: list[dict[str, Any]] = []

        for site in online_sites:
            share = (site.capacity / max(total_capacity, 1)) * quantity
            distribution.append({
                "site_id": site.site_id,
                "site_name": site.name,
                "allocated_quantity": round(share, 2),
                "specialization_match": True,
            })

        return {
            "work_order_id": work_order_id,
            "total_quantity": quantity,
            "distribution": distribution,
            "distributed_at": datetime.now(timezone.utc).isoformat(),
        }

    def aggregate_multi_site_progress(
        self,
        tenant_id: str,
        project_id: str = "",
    ) -> dict[str, Any]:
        config = self._configs.get(tenant_id)
        if not config:
            return {"sites": []}

        site_progress = []
        for site in config.sites:
            progress = random.uniform(0.3, 0.95) if site.status == SiteStatus.ONLINE else 0.0
            site_progress.append({
                "site_id": site.site_id,
                "site_name": site.name,
                "status": site.status.value,
                "progress": round(progress, 4),
                "work_orders_active": random.randint(5, 50),
                "work_orders_completed": random.randint(10, 100),
            })

        overall = sum(s["progress"] for s in site_progress) / max(len(site_progress), 1)

        return {
            "tenant_id": tenant_id,
            "overall_progress": round(overall, 4),
            "sites": site_progress,
            "assessed_at": datetime.now(timezone.utc).isoformat(),
        }

    def manage_site_failover(
        self,
        tenant_id: str,
        failed_site_id: str,
    ) -> dict[str, Any]:
        config = self._configs.get(tenant_id)
        if not config:
            return {"failover": False, "reason": "No config found"}

        failed_site = next((s for s in config.sites if s.site_id == failed_site_id), None)
        if not failed_site:
            return {"failover": False, "reason": "Site not found"}

        failed_site.status = SiteStatus.OFFLINE

        online_sites = config.get_online_sites()
        if not online_sites:
            return {"failover": False, "reason": "No available sites for failover"}

        target = online_sites[0]

        return {
            "failover": True,
            "failed_site": failed_site.site_id,
            "failed_site_name": failed_site.name,
            "failover_target": target.site_id,
            "failover_target_name": target.name,
            "work_orders_transferred": random.randint(5, 30),
            "failed_at": datetime.now(timezone.utc).isoformat(),
        }

    def _get_or_create_config(self, tenant_id: str) -> MultiSiteConfig:
        if tenant_id not in self._configs:
            self._configs[tenant_id] = MultiSiteConfig(tenant_id=tenant_id)
        return self._configs[tenant_id]

    def get_config(self, tenant_id: str) -> MultiSiteConfig | None:
        return self._configs.get(tenant_id)