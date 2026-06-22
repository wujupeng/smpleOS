"""AeroForge-X Certification Repository

Persistence layer for RequirementsTraceabilityService, RegulatoryLibraryService,
ComplianceChecklistService.
Target tables: regulatory_libraries, compliance_checklists
+ Neo4j graph for traceability (TraceNode, TraceLink)
"""

from __future__ import annotations

from typing import Any, Optional

from src.infrastructure.repositories.base_repository import (
    AsyncpgRepository,
    InMemoryRepository,
)


class CertificationRepository(InMemoryRepository):

    async def save_regulation(self, regulation: dict) -> None:
        self._put("regulatory_libraries", regulation["regulation_id"], regulation)

    async def get_regulation(self, regulation_id: str) -> Optional[dict]:
        return self._get("regulatory_libraries", regulation_id)

    async def list_regulations(self, **filters) -> list[dict]:
        return self._list("regulatory_libraries", **filters)

    async def save_checklist(self, checklist: dict) -> None:
        self._put("compliance_checklists", checklist["checklist_id"], checklist)

    async def get_checklist(self, checklist_id: str) -> Optional[dict]:
        return self._get("compliance_checklists", checklist_id)

    async def save_trace_node(self, node: dict) -> None:
        key = node["node_id"]
        if "trace_nodes" not in self._store:
            self._store["trace_nodes"] = {}
        self._store["trace_nodes"][key] = node

    async def get_trace_node(self, node_id: str) -> Optional[dict]:
        return self._store.get("trace_nodes", {}).get(node_id)

    async def list_trace_nodes(self, **filters) -> list[dict]:
        return self._list("trace_nodes", **filters)

    async def save_trace_link(self, link: dict) -> None:
        if "trace_links" not in self._store:
            self._store["trace_links"] = {}
        link_key = f"{link['source_id']}->{link['target_id']}"
        self._store["trace_links"][link_key] = link

    async def list_trace_links(self, **filters) -> list[dict]:
        return self._list("trace_links", **filters)


class AsyncpgCertificationRepository(AsyncpgRepository):

    async def save_regulation(self, regulation: dict) -> None:
        await self._execute(
            """
            INSERT INTO regulatory_libraries
                (regulation_id, regulation_type, title, version, amendment_history)
            VALUES ($1, $2, $3, $4, $5::jsonb)
            ON CONFLICT (regulation_id) DO UPDATE SET
                title = EXCLUDED.title,
                version = EXCLUDED.version,
                amendment_history = EXCLUDED.amendment_history
            """,
            regulation["regulation_id"],
            regulation["regulation_type"],
            regulation["title"],
            regulation["version"],
            self._json_dumps(regulation.get("amendment_history", [])),
        )

    async def get_regulation(self, regulation_id: str) -> Optional[dict]:
        row = await self._fetchrow(
            "SELECT * FROM regulatory_libraries WHERE regulation_id = $1",
            regulation_id,
        )
        if row is None:
            return None
        result = dict(row)
        result["amendment_history"] = self._json_loads(
            result.get("amendment_history", "[]")
        )
        return result

    async def list_regulations(self, **filters) -> list[dict]:
        rows = await self._fetch(
            "SELECT * FROM regulatory_libraries ORDER BY regulation_type, version"
        )
        results = []
        for r in rows:
            d = dict(r)
            d["amendment_history"] = self._json_loads(d.get("amendment_history", "[]"))
            results.append(d)
        if filters:
            results = [r for r in results if all(r.get(k) == v for k, v in filters.items())]
        return results

    async def save_checklist(self, checklist: dict) -> None:
        await self._execute(
            """
            INSERT INTO compliance_checklists
                (checklist_id, regulation_id, project_id, completion_percentage)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (checklist_id) DO UPDATE SET
                regulation_id = EXCLUDED.regulation_id,
                project_id = EXCLUDED.project_id,
                completion_percentage = EXCLUDED.completion_percentage
            """,
            checklist["checklist_id"],
            checklist["regulation_id"],
            checklist["project_id"],
            checklist.get("completion_percentage", 0.0),
        )

    async def get_checklist(self, checklist_id: str) -> Optional[dict]:
        row = await self._fetchrow(
            "SELECT * FROM compliance_checklists WHERE checklist_id = $1",
            checklist_id,
        )
        return dict(row) if row else None

    async def save_trace_node(self, node: dict) -> None:
        pass

    async def get_trace_node(self, node_id: str) -> Optional[dict]:
        return None

    async def list_trace_nodes(self, **filters) -> list[dict]:
        return []

    async def save_trace_link(self, link: dict) -> None:
        pass

    async def list_trace_links(self, **filters) -> list[dict]:
        return []