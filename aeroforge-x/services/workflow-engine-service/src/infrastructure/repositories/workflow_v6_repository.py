"""AeroForge-X Workflow Engine Repository

Persistence layer for ConfigurationChangeControlService, CertificationEvidenceAssemblyService,
SupplierCARService, ShopFloorEventEmitterService.
Target tables: configuration_change_requests, certification_evidence_packages, shop_floor_events
"""

from __future__ import annotations

from typing import Any, Optional

from src.infrastructure.repositories.base_repository import (
    AsyncpgRepository,
    InMemoryRepository,
)


class WorkflowV6Repository(InMemoryRepository):

    def save_change_request(self, cr: dict) -> None:
        self._put("configuration_change_requests", cr["request_id"], cr)

    def get_change_request(self, request_id: str) -> Optional[dict]:
        return self._get("configuration_change_requests", request_id)

    def list_change_requests(self, **filters) -> list[dict]:
        return self._list("configuration_change_requests", **filters)

    def save_evidence_package(self, pkg: dict) -> None:
        self._put("certification_evidence_packages", pkg["package_id"], pkg)

    def get_evidence_package(self, package_id: str) -> Optional[dict]:
        return self._get("certification_evidence_packages", package_id)

    def list_evidence_packages(self, **filters) -> list[dict]:
        return self._list("certification_evidence_packages", **filters)

    def save_shop_floor_event(self, event: dict) -> None:
        self._put("shop_floor_events", event["event_id"], event)

    def list_shop_floor_events(self, **filters) -> list[dict]:
        return self._list("shop_floor_events", **filters)

    def save_audit_entry(self, entry: dict) -> None:
        self._put("audit_trail", entry.get("audit_id", ""), entry)

    def list_audit_entries(self, **filters) -> list[dict]:
        return self._list("audit_trail", **filters)


class AsyncpgWorkflowV6Repository(AsyncpgRepository):

    async def save_change_request(self, cr: dict) -> None:
        await self._execute(
            """
            INSERT INTO configuration_change_requests
                (request_id, block_id, change_class, change_type, description,
                 requested_by, affected_items, impact_analysis, approval, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8::jsonb, $9::jsonb, $10)
            ON CONFLICT (request_id) DO UPDATE SET
                impact_analysis = EXCLUDED.impact_analysis,
                approval = EXCLUDED.approval,
                status = EXCLUDED.status
            """,
            cr["request_id"],
            cr["block_id"],
            cr["change_class"],
            cr["change_type"],
            cr["description"],
            cr["requested_by"],
            self._json_dumps(cr.get("affected_items", [])),
            self._json_dumps(cr.get("impact_analysis")),
            self._json_dumps(cr.get("approval")),
            cr.get("status", "Submitted"),
        )

    async def get_change_request(self, request_id: str) -> Optional[dict]:
        row = await self._fetchrow(
            "SELECT * FROM configuration_change_requests WHERE request_id = $1",
            request_id,
        )
        if row is None:
            return None
        result = dict(row)
        for key in ("affected_items", "impact_analysis", "approval"):
            result[key] = self._json_loads(result.get(key))
        return result

    async def list_change_requests(self, **filters) -> list[dict]:
        rows = await self._fetch(
            "SELECT * FROM configuration_change_requests ORDER BY created_at DESC"
        )
        results = []
        for r in rows:
            d = dict(r)
            for key in ("affected_items", "impact_analysis", "approval"):
                d[key] = self._json_loads(d.get(key))
            results.append(d)
        if filters:
            results = [r for r in results if all(r.get(k) == v for k, v in filters.items())]
        return results

    async def save_evidence_package(self, pkg: dict) -> None:
        await self._execute(
            """
            INSERT INTO certification_evidence_packages
                (package_id, checklist_id, project_id, is_complete, is_locked, version)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (package_id) DO UPDATE SET
                is_complete = EXCLUDED.is_complete,
                is_locked = EXCLUDED.is_locked,
                version = EXCLUDED.version
            """,
            pkg["package_id"],
            pkg["checklist_id"],
            pkg["project_id"],
            pkg.get("is_complete", False),
            pkg.get("is_locked", False),
            pkg.get("version", 1),
        )

    async def get_evidence_package(self, package_id: str) -> Optional[dict]:
        row = await self._fetchrow(
            "SELECT * FROM certification_evidence_packages WHERE package_id = $1",
            package_id,
        )
        return dict(row) if row else None

    async def list_evidence_packages(self, **filters) -> list[dict]:
        rows = await self._fetch(
            "SELECT * FROM certification_evidence_packages ORDER BY created_at DESC"
        )
        results = [dict(r) for r in rows]
        if filters:
            results = [r for r in results if all(r.get(k) == v for k, v in filters.items())]
        return results

    async def save_shop_floor_event(self, event: dict) -> None:
        await self._execute(
            """
            INSERT INTO shop_floor_events
                (event_id, event_type, source_equipment_id, payload)
            VALUES ($1, $2, $3, $4::jsonb)
            """,
            event["event_id"],
            event["event_type"],
            event.get("source_equipment_id"),
            self._json_dumps(event.get("payload", {})),
        )

    async def list_shop_floor_events(self, **filters) -> list[dict]:
        rows = await self._fetch(
            "SELECT * FROM shop_floor_events ORDER BY emitted_at DESC LIMIT 1000"
        )
        results = []
        for r in rows:
            d = dict(r)
            d["payload"] = self._json_loads(d.get("payload", "{}"))
            results.append(d)
        if filters:
            results = [r for r in results if all(r.get(k) == v for k, v in filters.items())]
        return results

    async def save_audit_entry(self, entry: dict) -> None:
        pass

    async def list_audit_entries(self, **filters) -> list[dict]:
        return []