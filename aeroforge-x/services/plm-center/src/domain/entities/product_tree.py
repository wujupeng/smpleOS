from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from aeroforge_common.domain.base import AggregateRoot
from aeroforge_common.utils.helpers import generate_code


class ProductNode:
    def __init__(
        self,
        part_id: str,
        name: str,
        part_type: str = "assembly",
        quantity: int = 1,
        version: str = "1.0",
        attributes: dict[str, Any] | None = None,
    ) -> None:
        self.part_id = part_id
        self.name = name
        self.part_type = part_type
        self.quantity = quantity
        self.version = version
        self.attributes = attributes or {}
        self.children: list[ProductNode] = []

    def add_child(self, child: ProductNode) -> None:
        self.children.append(child)

    def remove_child(self, child_id: str) -> bool:
        for i, child in enumerate(self.children):
            if child.part_id == child_id:
                self.children.pop(i)
                return True
        return False

    def find_child(self, part_id: str) -> ProductNode | None:
        for child in self.children:
            if child.part_id == part_id:
                return child
            found = child.find_child(part_id)
            if found:
                return found
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "part_id": self.part_id,
            "name": self.name,
            "part_type": self.part_type,
            "quantity": self.quantity,
            "version": self.version,
            "attributes": self.attributes,
            "children": [c.to_dict() for c in self.children],
        }


class ProductTree(AggregateRoot):
    def __init__(
        self,
        tree_id: str | None = None,
        name: str = "",
        spec_id: str | None = None,
        created_by: str = "",
    ) -> None:
        super().__init__(tree_id)
        self.name = name
        self.spec_id = spec_id
        self.root_node: ProductNode | None = None
        self.created_by = created_by
        self.created_at: datetime = datetime.now(timezone.utc)
        self.updated_at: datetime = datetime.now(timezone.utc)

    def set_root(self, node: ProductNode) -> None:
        self.root_node = node
        self.updated_at = datetime.now(timezone.utc)

    def add_part(self, parent_id: str, node: ProductNode) -> bool:
        if self.root_node is None:
            return False
        parent = self.root_node.find_child(parent_id)
        if parent is None and self.root_node.part_id == parent_id:
            parent = self.root_node
        if parent:
            parent.add_child(node)
            self.updated_at = datetime.now(timezone.utc)
            return True
        return False

    def remove_part(self, part_id: str) -> bool:
        if self.root_node is None:
            return False
        if self.root_node.part_id == part_id:
            self.root_node = None
            return True
        return self._remove_from_children(self.root_node, part_id)

    def _remove_from_children(self, parent: ProductNode, part_id: str) -> bool:
        for child in parent.children:
            if child.part_id == part_id:
                parent.remove_child(part_id)
                self.updated_at = datetime.now(timezone.utc)
                return True
            if self._remove_from_children(child, part_id):
                return True
        return False

    def where_used(self, part_id: str) -> list[str]:
        result: list[str] = []
        if self.root_node:
            self._find_parents(self.root_node, part_id, [], result)
        return result

    def _find_parents(self, node: ProductNode, target_id: str, path: list[str], result: list[str]) -> None:
        current_path = path + [node.part_id]
        for child in node.children:
            if child.part_id == target_id:
                result.extend(current_path)
            self._find_parents(child, target_id, current_path, result)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "spec_id": self.spec_id,
            "root_node": self.root_node.to_dict() if self.root_node else None,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }