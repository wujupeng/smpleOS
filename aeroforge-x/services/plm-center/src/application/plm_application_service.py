from __future__ import annotations

from typing import Any

from ..domain.entities.product_tree import ProductNode, ProductTree
from ..domain.services.product_structure_service import ProductStructureService
from ..domain.services.version_domain_service import Version, VersionDomainService
from ..infrastructure.persistence import ProductTreeRepository, VersionRepository


class PlmApplicationService:
    def __init__(self, tree_repo: ProductTreeRepository, version_repo: VersionRepository) -> None:
        self._tree_repo = tree_repo
        self._version_repo = version_repo
        self._structure_service = ProductStructureService()
        self._version_service = VersionDomainService()

    async def create_product_tree(self, name: str, spec_id: str, root_part_id: str, root_name: str, created_by: str) -> ProductTree:
        tree = ProductTree(name=name, spec_id=spec_id, created_by=created_by)
        root = ProductNode(part_id=root_part_id, name=root_name, part_type="assembly")
        tree.set_root(root)
        await self._tree_repo.save_tree(tree.to_dict())
        return tree

    async def get_product_tree(self, tree_id: str) -> dict[str, Any] | None:
        return await self._tree_repo.find_by_id(tree_id)

    async def add_part_to_tree(self, tree_id: str, parent_id: str, part_id: str, name: str, part_type: str = "part", quantity: int = 1) -> dict[str, Any] | None:
        tree_data = await self._tree_repo.find_by_id(tree_id)
        if tree_data is None:
            return None
        tree = self._reconstruct_tree(tree_data)
        success = self._structure_service.add_part(tree, parent_id, part_id, name, part_type, quantity)
        if success:
            await self._tree_repo.save_tree(tree.to_dict())
        return tree.to_dict() if success else None

    async def where_used(self, tree_id: str, part_id: str) -> list[str]:
        tree_data = await self._tree_repo.find_by_id(tree_id)
        if tree_data is None:
            return []
        tree = self._reconstruct_tree(tree_data)
        return self._structure_service.where_used(tree, part_id)

    async def create_version(self, object_id: str, change_summary: str, created_by: str, snapshot: dict[str, Any]) -> dict[str, Any]:
        versions = await self._version_repo.find_versions_by_object(object_id)
        current_major = versions[0]["major"] if versions else 0
        current_minor = versions[0]["minor"] if versions else 0
        version = self._version_service.create_version(object_id, change_summary, created_by, snapshot, current_major, current_minor)
        await self._version_repo.save_version(version.to_dict())
        return version.to_dict()

    async def get_version_history(self, object_id: str) -> list[dict[str, Any]]:
        return await self._version_repo.find_versions_by_object(object_id)

    async def compare_versions(self, object_id: str, major1: int, minor1: int, major2: int, minor2: int) -> dict[str, Any] | None:
        v1_data = await self._version_repo.find_version(object_id, major1, minor1)
        v2_data = await self._version_repo.find_version(object_id, major2, minor2)
        if v1_data is None or v2_data is None:
            return None
        v1 = Version(object_id=object_id, major=major1, minor=minor1, snapshot=v1_data.get("snapshot", {}))
        v2 = Version(object_id=object_id, major=major2, minor=minor2, snapshot=v2_data.get("snapshot", {}))
        return self._version_service.compare_versions(v1, v2)

    def _reconstruct_tree(self, data: dict[str, Any]) -> ProductTree:
        tree = ProductTree(tree_id=data["id"], name=data.get("name", ""), spec_id=data.get("spec_id"), created_by=data.get("created_by", ""))
        root_data = data.get("root_node")
        if root_data:
            tree.set_root(self._reconstruct_node(root_data))
        return tree

    def _reconstruct_node(self, data: dict[str, Any]) -> ProductNode:
        node = ProductNode(
            part_id=data["part_id"],
            name=data["name"],
            part_type=data.get("part_type", "part"),
            quantity=data.get("quantity", 1),
            version=data.get("version", "1.0"),
            attributes=data.get("attributes", {}),
        )
        for child_data in data.get("children", []):
            node.add_child(self._reconstruct_node(child_data))
        return node