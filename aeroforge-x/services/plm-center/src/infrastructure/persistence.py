from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


class ProductTreeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_tree(self, tree_data: dict[str, Any]) -> None:
        await self._session.execute(
            __import__("sqlalchemy").text(
                """INSERT INTO design_objects (id, object_code, object_type, name, description, attributes, created_by, created_at, updated_at)
                VALUES (:id, :object_code, 'product_tree', :name, :description, :attributes::jsonb, :created_by, :created_at, :updated_at)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name, attributes = EXCLUDED.attributes, updated_at = EXCLUDED.updated_at
                """
            ),
            {
                "id": tree_data["id"],
                "object_code": tree_data.get("name", ""),
                "name": tree_data.get("name", ""),
                "description": f"Product tree for spec {tree_data.get('spec_id', '')}",
                "attributes": __import__("json").dumps({"root_node": tree_data.get("root_node"), "spec_id": tree_data.get("spec_id")}),
                "created_by": tree_data.get("created_by", ""),
                "created_at": tree_data.get("created_at", ""),
                "updated_at": tree_data.get("updated_at", ""),
            },
        )

    async def find_by_id(self, tree_id: str) -> dict[str, Any] | None:
        result = await self._session.execute(
            __import__("sqlalchemy").text("SELECT * FROM design_objects WHERE id = :id AND object_type = 'product_tree'"),
            {"id": tree_id},
        )
        row = result.mappings().first()
        if row:
            data = dict(row)
            attrs = data.get("attributes", {})
            if isinstance(attrs, str):
                attrs = __import__("json").loads(attrs)
            return {**data, "root_node": attrs.get("root_node"), "spec_id": attrs.get("spec_id")}
        return None


class VersionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_version(self, version_data: dict[str, Any]) -> None:
        await self._session.execute(
            __import__("sqlalchemy").text(
                """INSERT INTO object_versions (id, object_id, major, minor, change_summary, snapshot, created_by, created_at)
                VALUES (:id, :object_id, :major, :minor, :change_summary, :snapshot::jsonb, :created_by, :created_at)
                """
            ),
            {
                "id": version_data["version_id"],
                "object_id": version_data["object_id"],
                "major": version_data["major"],
                "minor": version_data["minor"],
                "change_summary": version_data.get("change_summary", ""),
                "snapshot": __import__("json").dumps(version_data.get("snapshot", {})),
                "created_by": version_data.get("created_by", ""),
                "created_at": version_data.get("created_at", ""),
            },
        )

    async def find_versions_by_object(self, object_id: str) -> list[dict[str, Any]]:
        result = await self._session.execute(
            __import__("sqlalchemy").text(
                "SELECT * FROM object_versions WHERE object_id = :object_id ORDER BY major DESC, minor DESC"
            ),
            {"object_id": object_id},
        )
        return [dict(row) for row in result.mappings().all()]

    async def find_version(self, object_id: str, major: int, minor: int) -> dict[str, Any] | None:
        result = await self._session.execute(
            __import__("sqlalchemy").text(
                "SELECT * FROM object_versions WHERE object_id = :object_id AND major = :major AND minor = :minor"
            ),
            {"object_id": object_id, "major": major, "minor": minor},
        )
        row = result.mappings().first()
        return dict(row) if row else None