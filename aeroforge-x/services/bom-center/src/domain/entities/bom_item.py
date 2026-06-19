from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from aeroforge_common.domain.base import AggregateRoot, DomainEvent
from aeroforge_common.utils.helpers import generate_code


class BOMItem:
    def __init__(
        self,
        item_code: str,
        name: str,
        bom_type: str = "ebom",
        quantity: int = 1,
        unit: str = "ea",
        version: str = "1.0",
        part_type: str = "part",
        attributes: dict[str, Any] | None = None,
        station: str = "",
        assembly_order: int = 0,
        is_virtual: bool = False,
        mapping_status: str = "mapped",
        ebom_item_code: str = "",
    ) -> None:
        self.item_code = item_code
        self.name = name
        self.bom_type = bom_type
        self.quantity = quantity
        self.unit = unit
        self.version = version
        self.part_type = part_type
        self.attributes = attributes or {}
        self.children: list[BOMItem] = []
        self.station = station
        self.assembly_order = assembly_order
        self.is_virtual = is_virtual
        self.mapping_status = mapping_status
        self.ebom_item_code = ebom_item_code

    def add_child(self, child: BOMItem) -> None:
        self.children.append(child)

    def flatten(self) -> list[BOMItem]:
        result = [self]
        for child in self.children:
            result.extend(child.flatten())
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_code": self.item_code,
            "name": self.name,
            "bom_type": self.bom_type,
            "quantity": self.quantity,
            "unit": self.unit,
            "version": self.version,
            "part_type": self.part_type,
            "attributes": self.attributes,
            "station": self.station,
            "assembly_order": self.assembly_order,
            "is_virtual": self.is_virtual,
            "mapping_status": self.mapping_status,
            "ebom_item_code": self.ebom_item_code,
            "children": [c.to_dict() for c in self.children],
        }


class EBOM(AggregateRoot):
    def __init__(
        self,
        spec_id: str,
        created_by: str = "",
    ) -> None:
        super().__init__()
        self.ebom_code: str = generate_code("AAF-EBOM")
        self.spec_id = spec_id
        self.root_item: BOMItem | None = None
        self.status: str = "draft"
        self.created_by = created_by
        self.created_at: datetime = datetime.now(timezone.utc)

    def set_root(self, item: BOMItem) -> None:
        self.root_item = item

    def publish(self) -> None:
        if self.root_item is None:
            raise ValueError("Cannot publish empty eBOM")
        self.status = "published"
        event = DomainEvent(
            event_type="ebom.generated",
            aggregate_id=self.id,
            payload={
                "ebom_id": self.id,
                "ebom_code": self.ebom_code,
                "spec_id": self.spec_id,
                "top_level_item_code": self.root_item.item_code if self.root_item else None,
            },
        )
        self.add_domain_event(event)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "ebom_code": self.ebom_code,
            "spec_id": self.spec_id,
            "status": self.status,
            "root_item": self.root_item.to_dict() if self.root_item else None,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
        }


class MBOM(AggregateRoot):
    def __init__(
        self,
        ebom_id: str,
        created_by: str = "",
    ) -> None:
        super().__init__()
        self.mbom_code: str = generate_code("AAF-MBOM")
        self.ebom_id = ebom_id
        self.root_item: BOMItem | None = None
        self.status: str = "draft"
        self.unmapped_items: list[dict[str, Any]] = []
        self.validation_result: dict[str, Any] = {}
        self.created_by = created_by
        self.created_at: datetime = datetime.now(timezone.utc)

    def set_root(self, item: BOMItem) -> None:
        self.root_item = item

    def add_unmapped_item(self, item: dict[str, Any]) -> None:
        self.unmapped_items.append(item)

    def set_validation_result(self, result: dict[str, Any]) -> None:
        self.validation_result = result

    def publish(self) -> None:
        if self.root_item is None:
            raise ValueError("Cannot publish empty mBOM")
        if self.unmapped_items:
            raise ValueError("Cannot publish mBOM with unmapped items")
        self.status = "published"
        event = DomainEvent(
            event_type="mbom.generated",
            aggregate_id=self.id,
            payload={
                "mbom_id": self.id,
                "mbom_code": self.mbom_code,
                "ebom_id": self.ebom_id,
                "top_level_item_code": self.root_item.item_code if self.root_item else None,
            },
        )
        self.add_domain_event(event)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "mbom_code": self.mbom_code,
            "ebom_id": self.ebom_id,
            "status": self.status,
            "root_item": self.root_item.to_dict() if self.root_item else None,
            "unmapped_items": self.unmapped_items,
            "validation_result": self.validation_result,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
        }


class SBOM(AggregateRoot):
    def __init__(
        self,
        ebom_id: str,
        mbom_id: str = "",
        created_by: str = "",
    ) -> None:
        super().__init__()
        self.sbom_code: str = generate_code("AAF-SBOM")
        self.ebom_id = ebom_id
        self.mbom_id = mbom_id
        self.root_item: BOMItem | None = None
        self.status: str = "draft"
        self.created_by = created_by
        self.created_at: datetime = datetime.now(timezone.utc)

    def set_root(self, item: BOMItem) -> None:
        self.root_item = item

    def publish(self) -> None:
        if self.root_item is None:
            raise ValueError("Cannot publish empty sBOM")
        self.status = "published"
        event = DomainEvent(
            event_type="sbom.generated",
            aggregate_id=self.id,
            payload={
                "sbom_id": self.id,
                "sbom_code": self.sbom_code,
                "ebom_id": self.ebom_id,
                "mbom_id": self.mbom_id,
                "top_level_item_code": self.root_item.item_code if self.root_item else None,
            },
        )
        self.add_domain_event(event)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "sbom_code": self.sbom_code,
            "ebom_id": self.ebom_id,
            "mbom_id": self.mbom_id,
            "status": self.status,
            "root_item": self.root_item.to_dict() if self.root_item else None,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
        }