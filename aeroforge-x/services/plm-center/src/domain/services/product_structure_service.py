from __future__ import annotations

from typing import Any

from ..entities.product_tree import ProductNode, ProductTree


class ProductStructureService:
    def get_tree(self, tree: ProductTree) -> dict[str, Any] | None:
        return tree.to_dict()

    def add_part(self, tree: ProductTree, parent_id: str, part_id: str, name: str, part_type: str = "part", quantity: int = 1) -> bool:
        node = ProductNode(part_id=part_id, name=name, part_type=part_type, quantity=quantity)
        return tree.add_part(parent_id, node)

    def remove_part(self, tree: ProductTree, part_id: str) -> bool:
        return tree.remove_part(part_id)

    def where_used(self, tree: ProductTree, part_id: str) -> list[str]:
        return tree.where_used(part_id)